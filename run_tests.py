#!/usr/bin/env python3

import sys
import subprocess
from pathlib import Path
from datetime import datetime
import platform
from typing import List, Tuple
import colorama
from colorama import Fore, Style
import logging
from concurrent.futures import ThreadPoolExecutor
import re
import os

# Initialize colorama for cross-platform color support
colorama.init()

# Configure logging
def setup_logging(report_file: Path) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(report_file),
            logging.StreamHandler(sys.stdout)
        ]
    )

class TestRunner:
    def __init__(self):
        self.reports_dir = Path('reports')
        self.reports_dir.mkdir(exist_ok=True)
        
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.report_file = self.reports_dir / f"test_report_{self.timestamp}.txt"
        
        self.folders_to_test = ["game", "chat", "players"]
        self.global_status = 0
        
        # Setup logging
        setup_logging(self.report_file)
        
        # Platform-specific settings
        self.is_windows = platform.system().lower() == "windows"
        
    def run_command(self, cmd: List[str], shell: bool = False) -> Tuple[str, int]:
        """Execute a command and return its output and status code."""
        try:
            use_shell = shell or (self.is_windows and cmd[0] == "poetry")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=use_shell,
                universal_newlines=True,
                encoding='utf-8'
            )
            
            stdout, stderr = process.communicate()
            return f"{stdout}\n{stderr}".strip(), process.returncode
            
        except Exception as e:
            logging.error(f"Command execution failed: {e}")
            return str(e), 1

    def run_django_tests(self, folder: str) -> Tuple[str, int]:
        """Run Django tests for a specific folder."""
        cmd = ["poetry", "run", "python", "manage.py", "test", f"tests/{folder}/", "-v", "2"]
        return self.run_command(cmd)

    def run_coverage_report(self, folder: str) -> str:
        """Generate coverage report for a specific folder."""
        cmd = ["poetry", "run", "coverage", "report", "-m", f"--include=tests/{folder}/*,{folder}/*"]
        output, _ = self.run_command(cmd)
        return output

    def format_output(self, text: str, color: str = "") -> str:
        """Format text with color for console output."""
        return f"{color}{text}{Style.RESET_ALL}"

    def write_report(self, content: str, color: str = "") -> None:
        """Write content to both console and report file."""
        print(self.format_output(content, color))
        
        with open(self.report_file, 'a', encoding='utf-8') as f:
            clean_content = re.sub(r'\033\[[0-9;]*[mK]', '', content)
            f.write(f"{clean_content}\n")

    def run_tests(self) -> int:
        """Main method to run all tests."""
        self.write_report(f"Test Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.write_report("=" * 20)
        
        logging.info(f"Debug: Will write to file: {self.report_file}")

        for folder in self.folders_to_test:
            self.write_report(f"\nRunning tests for {folder}", Fore.CYAN)
            
            # Run Django tests
            self.write_report("Running Django tests...", Style.BRIGHT)
            test_output, test_status = self.run_django_tests(folder)
            self.write_report(test_output)
            
            if test_status != 0:
                self.global_status = 1
            
            # Run coverage report
            self.write_report("\nCoverage Report", Style.BRIGHT)
            self.write_report("=" * 18)
            coverage_output = self.run_coverage_report(folder)
            self.write_report(coverage_output)
            
            self.write_report(f"End of tests for {folder}")

        # Final summary
        self.write_report("\nTest Summary", Style.BRIGHT)
        self.write_report("=" * 18)
        
        if self.global_status == 0:
            self.write_report("All tests completed successfully!", Fore.GREEN)
        else:
            self.write_report("Some tests failed!", Fore.RED)
        
        self.write_report(f"\nReport saved to: {self.report_file}")
        
        return self.global_status

def main():
    runner = TestRunner()
    sys.exit(runner.run_tests())

if __name__ == "__main__":
    main()

