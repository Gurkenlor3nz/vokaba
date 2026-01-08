from cx_Freeze import setup, Executable

setup(
    name='Vokaba',
    version='0.0.1_alpha',
    executables=[Executable('main.py')],
)