.pragma library

var pt = {
    "You made a wise decision by choosing to install this system.": "Você tomou uma decisão sábia ao optar por instalar este sistema.",
    "Language": "Idioma",
    "Choose the language": "Escolha o idioma",
    "Installation requirements need attention": "Os requisitos de instalação precisam de atenção",
    "A required condition is not satisfied. Review the items below before continuing.": "Uma condição obrigatória não foi atendida. Revise os itens abaixo antes de continuar.",
    "BigLinux logo surrounded by slowly moving rings": "Logo do BigLinux cercado por anéis em movimento lento",

    "Location and language": "Localização e idioma",
    "Choose the time zone, system language and regional formats.": "Escolha o fuso horário, o idioma do sistema e os formatos regionais.",
    "Time zone": "Fuso horário",
    "Region": "Região",
    "Zone": "Zona",
    "Language and regional formats": "Idioma e formatos regionais",
    "System language": "Idioma do sistema",
    "Regional formats": "Formatos regionais",
    "Current time zone: %1": "Fuso horário atual: %1",
    "Time zone: %1": "Fuso horário: %1",
    "Select the area closest to you so the clock and daylight-saving rules are correct.": "Selecione a área mais próxima para que o relógio e as regras de horário de verão fiquem corretos.",
    "Click the map to choose the nearest time zone.": "Clique no mapa para escolher o fuso horário mais próximo.",
    "Example: %1": "Exemplo: %1",

    "User account": "Conta de usuário",
    "This password is not the disk password": "Esta senha não é a senha do disco",
    "The disk password cannot be typed at boot": "A senha do disco não pode ser digitada na inicialização",
    "The password you set on the previous screen unlocks the disk at boot. The one below is for signing in to your account.": "A senha definida na tela anterior destrava o disco na inicialização. A de baixo é para entrar na sua conta.",
    "The password you set on the previous screen unlocks the disk at boot, and must have no accents and no letter c-cedilla. The one below is for signing in to your account.": "A senha definida na tela anterior destrava o disco na inicialização e não pode ter acentos nem a letra ç. A de baixo é para entrar na sua conta.",
    "Go back and remove the accents and the letter c-cedilla from it: the boot keyboard cannot type them, and the disk would not unlock.": "Volte e remova os acentos e a letra ç: o teclado da inicialização não digita esses caracteres e o disco não seria destravado.",
    "Create your account and choose the name used by this computer on the network.": "Crie sua conta e escolha o nome usado por este computador na rede.",
    "Identity": "Identidade",
    "Your name": "Seu nome",
    "Full name": "Nome completo",
    "Login name": "Nome de usuário",
    "Computer name": "Nome do computador",
    "Password": "Senha",
    "Repeat password": "Repita a senha",
    "Root password": "Senha do root",
    "Repeat root password": "Repita a senha do root",
    "Use the user password for the administrator account": "Usar a senha do usuário para a conta de administrador",
    "Log in automatically": "Entrar automaticamente",
    "Require a strong password": "Exigir uma senha forte",
    "Only lowercase letters, numbers, underscore and hyphen are allowed.": "Use apenas letras minúsculas, números, sublinhado e hífen.",
    "The login name root is reserved.": "O nome de usuário root é reservado.",
    "Use letters, numbers, underscore and hyphen, with at least two characters.": "Use letras, números, sublinhado e hífen, com pelo menos dois caracteres.",
    "The computer name localhost is reserved.": "O nome de computador localhost é reservado.",
    "The passwords do not match.": "As senhas não coincidem.",
    "The passwords match.": "As senhas coincidem.",
    "Show passwords": "Mostrar senhas",
    "Security": "Segurança",
    "Account preview": "Prévia da conta",

    "Review": "Revisão",
    "Pong game": "Jogo Pong",
    "Move the left paddle with the mouse or the up and down arrow keys. Press Space to pause or resume.": "Mova a raquete da esquerda com o mouse ou com as setas para cima e para baixo. Pressione Espaço para pausar ou continuar.",
    "Mouse or ↑ ↓ / W S to move • Space to pause": "Mouse ou ↑ ↓ / W S para mover • Espaço para pausar",
    "Paused": "Pausado",
    "Press Space or use the button below to continue": "Pressione Espaço ou use o botão abaixo para continuar",
    "Resume": "Continuar",
    "Pause": "Pausar",
    "Pause or resume the Pong game": "Pausar ou continuar o jogo Pong",
    "Nothing will be changed until you review and confirm.": "Nada será alterado até você revisar e confirmar.",
    "Check the choices below. The disks will not be changed until you confirm the installation.": "Confira as escolhas abaixo. Os discos não serão alterados até você confirmar a instalação.",
    "You can still go back and adjust any choice before starting the installation.": "Você ainda pode voltar e ajustar qualquer escolha antes de iniciar a instalação.",

    "Installation completed": "Instalação concluída",
    "Installation interrupted": "Instalação interrompida",
    "The installer encountered an error and will close. Review the error details before trying again.": "O instalador encontrou um erro e será fechado. Revise os detalhes antes de tentar novamente.",
    "BigLinux has been installed on your computer.": "O BigLinux foi instalado no seu computador.",
    "You may restart into the new system or continue using the live environment.": "Você pode reiniciar no novo sistema ou continuar usando o ambiente live.",
    "Restart system": "Reiniciar o sistema",
    "The installation log is available in the live user's home directory and in /var/log/installation.log on the installed system.": "O registro da instalação está disponível na pasta pessoal do usuário live e em /var/log/installation.log no sistema instalado."
}

function isPortuguese(localeKey) {
    var localeName = String(localeKey).split("|")[0].toLowerCase()
    return localeName === "pt" || localeName.indexOf("pt_") === 0 || localeName.indexOf("pt-") === 0
}

function translate(source, localeKey) {
    if (isPortuguese(localeKey) && pt[source] !== undefined) return pt[source]
    return source
}
