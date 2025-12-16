def yes_no_input(prompt: str, default: bool=False) -> bool:
    while True:
        user_input = input(f"{prompt} (y/n, defaults to {'y' if default else 'n'}): ")
        if (user_input == 'Y') or (user_input == 'y') or (default and (user_input == '')):
            return True
        elif (user_input == 'N') or (user_input == 'n') or ((not default) and (user_input == '')):
            return False
        else:
            print("\033[31mInvalid input!\033[0m")
