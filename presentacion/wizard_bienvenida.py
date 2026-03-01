from __future__ import annotations


class WizardBienvenida:
    Accepted = 1

    def __new__(cls, *args, **kwargs):
        from app.ui.wizard_bienvenida.wizard import WizardBienvenida as WizardBienvenidaReal

        return WizardBienvenidaReal(*args, **kwargs)


__all__ = ["WizardBienvenida"]
