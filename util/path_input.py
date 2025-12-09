from .check_path_availability import check_path_availability

def path_input(prompt, type, default=None, exist=False):
    """
    User input path
    
    :param prompt: prompt text
    :param type: file or dir
    :param default: optional. default value
    :param exist: optional. True or False, defaults to False. whether the path must exist
    """
    while True:
        prompt_str = prompt
        if default is not None:
            prompt_str += f"({default:<f})"
        prompt_str += ': '
        user_input = input(prompt_str)
        if (default is not None) and (user_input == ''):
            return default
        path_availability = check_path_availability(user_input)
        if (path_availability == 'file' and type == 'file') or (path_availability == 'dir' and type == 'dir'):
            return user_input
        elif (path_availability == 'file' and type == 'dir'):
            print("\033[31mA path to a directory is required, while a path to a file is provided!\033[0m")
        elif (path_availability == 'dir' and type == 'file'):
            print("\033[31mA path to a file is required, while a path to a directory is provided!\033[0m")
        elif not exist:
            return user_input
        else:
            print("\033[31mInvalid input!\033[0m")
