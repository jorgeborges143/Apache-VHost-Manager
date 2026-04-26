"""
Unit tests for Apache command wrappers using mocks.
"""

import pytest
from unittest.mock import patch, MagicMock
from app.apache.service import (
    apache_status,
    start_apache,
    stop_apache,
    restart_apache,
    reload_apache,
    configtest_result,
    run_a2ensite,
    run_a2dissite
)


class TestApacheService:
    @patch('app.apache.service.subprocess.run')
    def test_apache_status_running(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')
        assert apache_status() is True
        mock_run.assert_called_once_with(
            ['systemctl', 'is-active', '--quiet', 'apache2'],
            capture_output=True, text=True, check=False
        )

    @patch('app.apache.service.subprocess.run')
    def test_apache_status_stopped(self, mock_run):
        mock_run.return_value = MagicMock(returncode=3, stdout='', stderr='')
        assert apache_status() is False

    @patch('app.apache.service.subprocess.run')
    def test_start_apache(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout='Started', stderr='')
        result = start_apache()
        assert result['success'] is True
        mock_run.assert_called_once_with(
            ['sudo', 'systemctl', 'start', 'apache2'],
            capture_output=True, text=True, check=False
        )

    @patch('app.apache.service.subprocess.run')
    def test_stop_apache(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout='Stopped', stderr='')
        result = stop_apache()
        assert result['success'] is True

    @patch('app.apache.service.subprocess.run')
    def test_restart_apache(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')
        result = restart_apache()
        assert result['success'] is True

    @patch('app.apache.service.subprocess.run')
    def test_reload_apache(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')
        result = reload_apache()
        assert result['success'] is True

    @patch('app.apache.service.subprocess.run')
    def test_configtest_valid(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='',
            stderr='Syntax OK'
        )
        result = configtest_result()
        assert result['valid'] is True
        assert 'Syntax OK' in result['message']

    @patch('app.apache.service.subprocess.run')
    def test_configtest_invalid(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout='',
            stderr='Syntax error on line 5'
        )
        result = configtest_result()
        assert result['valid'] is False

    @patch('app.apache.service.subprocess.run')
    def test_a2ensite_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout='Enabling site example.', stderr='')
        result = run_a2ensite('example.com.conf')
        assert result['success'] is True
        mock_run.assert_called_once_with(
            ['sudo', 'a2ensite', 'example.com.conf'],
            capture_output=True, text=True, check=False
        )

    @patch('app.apache.service.subprocess.run')
    def test_a2dissite_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout='Disabling site example.', stderr='')
        result = run_a2dissite('example.com.conf')
        assert result['success'] is True

    def test_a2ensite_unsafe_filename(self):
        with pytest.raises(ValueError, match='Unsafe filename'):
            run_a2ensite('../../etc/passwd')

    def test_a2dissite_unsafe_filename(self):
        with pytest.raises(ValueError, match='Unsafe filename'):
            run_a2dissite('site; rm -rf /')

    @patch('app.apache.service.subprocess.run')
    def test_command_file_not_found(self, mock_run):
        mock_run.side_effect = FileNotFoundError('apache2ctl not found')
        result = configtest_result()
        assert result['valid'] is False
        assert 'apache2ctl not found' in result['message']

