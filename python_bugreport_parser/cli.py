import argparse
from dataclasses import dataclass


@dataclass
class CliArgs:
    """Data class for storing CLI arguments"""

    file_name: str  # 必填的位置参数
    mode: str


def parse_cli() -> CliArgs:
    parser = argparse.ArgumentParser(description="处理文件的CLI工具")
    parser.add_argument("file_name", type=str, help="File name")
    parser.add_argument(
        "-m",
        "--mode",
        type=str,
        choices=["a", "b"],
        default="a",
        help="处理模式，可选值：a 或 b，默认为 a",
    )
    args = parser.parse_args()
    return CliArgs(**vars(args))  # 将命名空间转换为数据类对象


if __name__ == "__main__":
    cli_args = parse_cli()
