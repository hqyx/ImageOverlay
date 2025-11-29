import sys
import os
import winreg

def register_context_menu():
    # Get the path of the executable
    exe_path = os.path.abspath("dist\\ImageOverlay.exe")
    if not os.path.exists(exe_path):
        print(f"Error: Executable not found at {exe_path}")
        print("Please make sure you have built the application first.")
        return

    key_path = r"*\shell\OpenWithImageOverlay"
    
    try:
        # Create the main key
        key = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, key_path)
        winreg.SetValue(key, "", winreg.REG_SZ, "Open with Image Overlay")
        winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, exe_path)
        winreg.CloseKey(key)

        # Create the command key
        command_key = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, key_path + r"\command")
        winreg.SetValue(command_key, "", winreg.REG_SZ, f'"{exe_path}" "%1"')
        winreg.CloseKey(command_key)
        
        print("Successfully added 'Open with Image Overlay' to context menu!")
        
    except Exception as e:
        print(f"Failed to register context menu: {e}")
        print("Note: You may need to run this script as Administrator.")

if __name__ == "__main__":
    register_context_menu()
