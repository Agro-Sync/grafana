"""
    AWS Academy Credential Extractor using Playwright
    This module automates the process of logging into AWS Academy, retrieving AWS credentials,
    and storing them in a file for use in GitHub workflows or other CI/CD environments.
    Classes:
        AWS: Handles browser automation for AWS Academy login and credential retrieval.
    Functions:
        set_github_env: Writes AWS credentials to a file for environment variable configuration.
    Usage:
        Set EMAIL and PASSWORD environment variables, then run the script to automatically
        extract and save AWS credentials from AWS Academy.
"""

from playwright.sync_api import sync_playwright

import time
import logging

logging.basicConfig(level=logging.INFO)


class AWS:
    """
    Automates login and credential retrieval from AWS Academy using Playwright.
    Args:
        email (str): User email for AWS Academy login.
        password (str): User password for AWS Academy login.
        headless (bool, optional): Whether to run browser in headless mode. Defaults to True.
    Attributes:
        playwright: Playwright instance.
        browser: Chromium browser instance.
        context: Browser context.
        page: Current browser page.
        screenshots (str): Directory to save screenshots.
    Methods:
        _login(email, password):
            Logs into AWS Academy portal using provided credentials.
        configure_aws(conta):
            Navigates to AWS Academy course, ensures account is active, and retrieves AWS credentials.
        get_secrets(info_raw: str) -> tuple[str, str, str]:
            Parses raw credential string and returns AWS access key ID, secret access key, and session token.
    """

    def __init__(self, email: str, password: str, headless=True):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=headless)
        self.context = self.browser.new_context()
        self.page = self.context.new_page()
        self.screenshots = "screenshots"

        logging.info("[+] Navegador iniciado")
        self._login(email, password)

    def _login(self, email: str, password: str) -> None:
        """
        Authenticates a user to AWS Academy platform using provided credentials.
        This method automates the login process by:
        1. Navigating to the AWS Academy login page
        2. Clicking the login button
        3. Filling in email and password fields
        4. Submitting the login form
        5. Waiting for successful authentication confirmation
        Takes screenshots at each step for debugging purposes.
        Args:
            email (str): The user's email address for authentication.
            password (str): The user's password for authentication.
        Returns:
            None
        Raises:
            Exception: If login fails due to invalid credentials or if the page layout has changed,
                        preventing successful authentication within the 15-second timeout.
        Note:
            Screenshots are saved to track the login progress and for troubleshooting failed attempts.
        """

        logging.info("[*] Fazendo login...")
        self.page.goto("https://www.awsacademy.com/vforcesite/LMS_Login")

        self.page.click('body > div.splash-body > a:nth-child(1) > button')
        self.page.screenshot(path=f"{self.screenshots}/1-click_start.png")

        self.page.fill("#pseudonym_session_unique_id", email)
        self.page.fill("#pseudonym_session_password", password)
        self.page.screenshot(path=f"{self.screenshots}/2-send_data.png")

        self.page.click(
            '#login_form > div.ic-Login__actions > div.ic-Form-control.ic-Form-control--login > input'
        )

        try:
            self.page.wait_for_url(
                "https://awsacademy.instructure.com/?login_success=1", timeout=15000)
            logging.info("[+] Login concluído com sucesso")
            self.page.screenshot(
                path=f"{self.screenshots}/3-conclude_login.png")
        except Exception:
            logging.error(
                "[!] Falha no login: credenciais inválidas ou página não carregou corretamente")
            self.page.screenshot(path=f"{self.screenshots}/3-login_error.png")
            raise Exception(
                "Login falhou! Verifique suas credenciais ou se o site mudou o layout."
            )

    def configure_aws(self, conta) -> str:
        """
        Configure and retrieve AWS credentials from AWS Academy.
        This method navigates to the AWS Academy module, verifies the account status,
        starts the AWS lab environment if needed, and retrieves the AWS credentials.
        Args:
            conta (str): The course ID for AWS Academy.
        Returns:
            str: The AWS credentials text content retrieved from the credentials box.
        Raises:
            TimeoutError: If any element fails to load within the specified timeout.
        Process:
            1. Navigate to the AWS Academy course module
            2. Check the status of the AWS lab environment
            3. Launch the AWS lab if not already running (led-green status)
            4. Click buttons to display AWS credentials
            5. Extract and return the credentials text
        """

        logging.info("[+] Entrando na AWS")
        self.page.goto(
            f"https://awsacademy.instructure.com/courses/{conta}/modules/items/12498015")
        self.page.wait_for_load_state("domcontentloaded", timeout=0)
        self.page.screenshot(path=f"{self.screenshots}/4-configure_aws.png")

        logging.info('[*] Verificando status da conta')
        frame_locator = self.page.frame_locator('iframe.tool_launch')
        locator = frame_locator.locator('#vmstatus')
        locator.wait_for(state='attached', timeout=30000)
        classe = locator.get_attribute('class')
        self.page.screenshot(
            path=f"{self.screenshots}/5-configure_aws_status.png")

        if 'led-green' not in classe:
            logging.info('[*] Inicia a conta da AWS')
            frame_locator.locator('#launchclabsbtn').click()
            frame_locator.locator('#vmstatus.led-green').wait_for(timeout=0)

        logging.info("[*] Coletando informações da AWS")
        # mostrar informações aws
        frame_locator.locator('#detailbtn2').click()
        frame_locator.locator('#clikeyboxbtn').click()
        self.page.screenshot(
            path=f"{self.screenshots}/6-show_aws_credentials.png")

        # coletar texto
        text_locator = frame_locator.locator('#clikeybox > pre > span')
        text_locator.wait_for(state='attached', timeout=0)
        return text_locator.text_content()

    @staticmethod
    def get_secrets(info_raw: str) -> tuple[str, str, str]:
        """
        Extract AWS credentials from a raw information string.
        Parses a formatted string containing AWS access key ID, secret access key,
        and session token, and returns them as a tuple.
        Args:
            info_raw (str): A raw string containing AWS credentials in the format:
                           "... aws_access_key_id=<key> aws_secret_access_key=<secret> aws_session_token=<token>"
        Returns:
            tuple[str, str, str]: A tuple containing:
                                 - aws_access_key_id (str): The AWS access key ID
                                 - aws_secret_access_key (str): The AWS secret access key
                                 - aws_session_token (str): The AWS session token
        Raises:
            IndexError: If the input string does not contain the expected format with at least 4 space-separated values.
        """

        info = info_raw.split()

        aws_access_key_id = info[1].split('=')[1]
        aws_secret_access_key = info[2].split('=')[1]
        aws_session_token = info[3].split('=', 1)[1]
        logging.info('[+] Dados coletados')
        return aws_access_key_id, aws_secret_access_key, aws_session_token


def set_github_env(aws_access_key_id: str, aws_secret_access_key: str, aws_session_token: str) -> None:
    """
    Write AWS credentials to a file for GitHub environment configuration.
    This function appends AWS access credentials (access key ID, secret access key,
    and session token) to a 'creds.txt' file in the current directory. These credentials
    can be used to configure GitHub Actions workflows or other CI/CD environments.
    Args:
        aws_access_key_id (str): The AWS access key ID credential.
        aws_secret_access_key (str): The AWS secret access key credential.
        aws_session_token (str): The AWS session token credential.
    Returns:
        None
    Note:
        - Credentials are appended to 'creds.txt' in the current working directory.
        - Ensure proper file permissions and security measures are in place to protect
          sensitive credentials.
        - Consider using environment variables or secure credential management instead
          of storing credentials in files.
    """

    with open('creds.txt', 'a') as env_file:
        env_file.write(f"AWS_ACCESS_KEY_ID={aws_access_key_id}\n")
        env_file.write(f"AWS_SECRET_ACCESS_KEY={aws_secret_access_key}\n")
        env_file.write(f"AWS_SESSION_TOKEN={aws_session_token}\n")


if __name__ == "__main__":
    import os

    EMAIL = os.environ["EMAIL"]
    SENHA = os.environ["PASSWORD"]
    CONTA = "130670"

    aws = AWS(EMAIL, SENHA)
    page = aws.page
    try:
        info_raw = aws.configure_aws(CONTA)
        aws_access_key_id, aws_secret_access_key, aws_session_token = aws.get_secrets(
            info_raw)
        set_github_env(aws_access_key_id,
                       aws_secret_access_key, aws_session_token)
    except Exception as error:
        screenshot_dir = "screenshots"
        os.makedirs(screenshot_dir, exist_ok=True)
        timestamp = int(time.time())
        path = os.path.join(
            screenshot_dir, f"screenshot_error_{timestamp}.png"
        )
        page.screenshot(path=path)
        logging.info(f"Screenshot salvo em: {path}")
        raise Exception(error)
