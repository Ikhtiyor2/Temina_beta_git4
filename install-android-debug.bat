@echo off
REM Обновление приложения: переходит в temina-android и ставит debug-сборку на телефон по USB.
REM Положи ярлык или запускай из корня репозитория Temina_beta_git.

setlocal
cd /d "%~dp0temina-android"
if not exist "gradlew.bat" (
    echo Не найден temina-android\gradlew.bat
    exit /b 1
)
call gradlew.bat :app:installDebug --no-daemon
exit /b %ERRORLEVEL%
