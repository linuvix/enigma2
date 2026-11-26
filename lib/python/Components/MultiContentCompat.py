# OpenPLi MultiContent compatibility layer

import sys


def installMultiContentCompat():

    patched_classes = set()

    for module in list(sys.modules.values()):

        if module is None:
            continue

        try:
            cls = getattr(module, "eFlexBoxPythonMultiContent", None)
        except Exception:
            continue

        if cls is None or cls in patched_classes:
            continue

        if getattr(cls, "_openpli_gfont_compat", False):
            continue

        try:
            original_setFont = cls.setFont

            def make_safe_setFont(original):

                def safe_setFont(self, *args, **kwargs):

                    try:
                        return original(self, *args, **kwargs)

                    except Exception as error:

                        if "gFont" in str(error):
                            print(
                                "[OpenPLi MultiContent] "
                                "Incompatible gFont ignored:",
                                error
                            )
                            return None

                        raise

                return safe_setFont

            cls.setFont = make_safe_setFont(original_setFont)
            cls._openpli_gfont_compat = True

            patched_classes.add(cls)

            print(
                "[OpenPLi MultiContent] "
                "gFont compatibility installed"
            )

        except Exception as error:
            print(
                "[OpenPLi MultiContent] "
                "Unable to patch class:",
                error
            )
