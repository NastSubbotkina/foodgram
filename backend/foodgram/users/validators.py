from django.core.validators import RegexValidator

username_validator = RegexValidator(
    regex=r'^[\w.@+-]+\Z',
    message='Имя пользователя может содержать только буквы,'
    ' цифры и символы @/./+/-/_.',
)
