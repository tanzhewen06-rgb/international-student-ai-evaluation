"""Save API keys in Windows Credential Manager, outside the project files."""
import getpass
import warnings

from keyring.backends.Windows import WinVaultKeyring


def main():
    vault = WinVaultKeyring()
    print("Keys are saved in Windows Credential Manager, not in project files.")
    print("Input is hidden. Press Enter to skip a provider or keep its existing key.")
    for name in ("GEMINI_API_KEY", "OPENAI_API_KEY"):
        with warnings.catch_warnings():
            # Refuse an input method that would echo a secret on screen.
            warnings.simplefilter("error", getpass.GetPassWarning)
            value = getpass.getpass(f"{name}: ").strip()
        if value:
            vault.set_password("AI Persona Analysis", name, value)
            print(f"{name} saved.")
        else:
            print(f"{name} unchanged.")


if __name__ == "__main__":
    main()
