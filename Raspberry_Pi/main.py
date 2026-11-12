from cli import main as run_application


def main() -> None:
    run_application()


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nZakończono pracę systemu.")
