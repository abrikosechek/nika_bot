"""
Реестр всех доступных модулей бота.

Для добавления нового модуля:
1. Создайте класс модуля в src/modules/<name>/
2. Импортируйте его здесь
3. Добавьте в ALL_MODULES
"""

from src.modules.fun import RollModule
from src.modules.verification import VerificationModule
from src.modules.god import GodModule
from src.modules.private_channels import PrivateModule

# Список всех модулей для загрузки
ALL_MODULES = [
    RollModule,
    VerificationModule,
    GodModule,
    PrivateModule,
]

__all__ = ['ALL_MODULES']
