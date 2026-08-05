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
    "If you encrypt the disk, the password cannot have accents or the letter c-cedilla": "Se criptografar o disco, a senha não pode ter acentos nem a letra ç",
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

// Portuguese carries the whole interface. The other languages carry the one
// string that must not be missed whatever the installer runs in: a disk
// password it rules out leaves a machine nobody can unlock at boot.
var byLanguage = {
    "be": {
        "If you encrypt the disk, the password cannot have accents or the letter c-cedilla": "Калі вы зашыфруеце дыск, пароль не можа мець дыякрытычных знакаў ці літары ç"
    },
    "bg": {
        "If you encrypt the disk, the password cannot have accents or the letter c-cedilla": "Ако шифровате диска, паролата не може да съдържа знаци с ударение или буквата ç"
    },
    "cs": {
        "If you encrypt the disk, the password cannot have accents or the letter c-cedilla": "Pokud disk zašifrujete, heslo nesmí obsahovat diakritiku ani znak ç"
    },
    "da": {
        "If you encrypt the disk, the password cannot have accents or the letter c-cedilla": "Hvis du krypterer disken, må adgangskoden ikke indeholde accenttegn eller bogstavet ç"
    },
    "de": {
        "If you encrypt the disk, the password cannot have accents or the letter c-cedilla": "Wenn Sie die Festplatte verschlüsseln, darf das Passwort keine Akzente und kein ç enthalten"
    },
    "el": {
        "If you encrypt the disk, the password cannot have accents or the letter c-cedilla": "Αν κρυπτογραφήσετε τον δίσκο, ο κωδικός δεν μπορεί να έχει τόνους ή το γράμμα ç"
    },
    "es": {
        "If you encrypt the disk, the password cannot have accents or the letter c-cedilla": "Si cifra el disco, la contraseña no puede tener acentos ni la letra ç"
    },
    "et": {
        "If you encrypt the disk, the password cannot have accents or the letter c-cedilla": "Kui krüpteerite ketta, ei tohi paroolis olla täpitähti ega tähte ç"
    },
    "fi": {
        "If you encrypt the disk, the password cannot have accents or the letter c-cedilla": "Jos salaat levyn, salasanassa ei voi olla aksentteja eikä ç-kirjainta"
    },
    "fr": {
        "If you encrypt the disk, the password cannot have accents or the letter c-cedilla": "Si vous chiffrez le disque, le mot de passe ne peut pas contenir d'accents ni la lettre ç"
    },
    "he": {
        "If you encrypt the disk, the password cannot have accents or the letter c-cedilla": "אם תצפין את הדיסק, הסיסמה לא יכולה לכלול סימני הטעמה או האות ç"
    },
    "hr": {
        "If you encrypt the disk, the password cannot have accents or the letter c-cedilla": "Ako šifrirate disk, lozinka ne može sadržavati dijakritičke znakove ni slovo ç"
    },
    "hu": {
        "If you encrypt the disk, the password cannot have accents or the letter c-cedilla": "Ha titkosítja a lemezt, a jelszó nem tartalmazhat ékezetes karaktert vagy ç betűt"
    },
    "is": {
        "If you encrypt the disk, the password cannot have accents or the letter c-cedilla": "Ef þú dulkóðar diskinn má lykilorðið ekki innihalda broddstafi eða bókstafinn ç"
    },
    "it": {
        "If you encrypt the disk, the password cannot have accents or the letter c-cedilla": "Se cifri il disco, la password non può contenere accenti né la lettera ç"
    },
    "ja": {
        "If you encrypt the disk, the password cannot have accents or the letter c-cedilla": "ディスクを暗号化する場合、パスワードにアクセント記号や ç は使用できません"
    },
    "ko": {
        "If you encrypt the disk, the password cannot have accents or the letter c-cedilla": "디스크를 암호화하면 비밀번호에 악센트 문자나 ç 를 사용할 수 없습니다"
    },
    "nl": {
        "If you encrypt the disk, the password cannot have accents or the letter c-cedilla": "Als u de schijf versleutelt, mag het wachtwoord geen accenttekens of de letter ç bevatten"
    },
    "no": {
        "If you encrypt the disk, the password cannot have accents or the letter c-cedilla": "Hvis du krypterer disken, kan ikke passordet inneholde aksenttegn eller bokstaven ç"
    },
    "pl": {
        "If you encrypt the disk, the password cannot have accents or the letter c-cedilla": "Jeśli zaszyfrujesz dysk, hasło nie może zawierać znaków diakrytycznych ani litery ç"
    },
    "ro": {
        "If you encrypt the disk, the password cannot have accents or the letter c-cedilla": "Dacă criptați discul, parola nu poate conține diacritice sau litera ç"
    },
    "ru": {
        "If you encrypt the disk, the password cannot have accents or the letter c-cedilla": "Если вы зашифруете диск, пароль не может содержать символы с диакритикой или букву ç"
    },
    "sk": {
        "If you encrypt the disk, the password cannot have accents or the letter c-cedilla": "Ak disk zašifrujete, heslo nesmie obsahovať diakritiku ani znak ç"
    },
    "sv": {
        "If you encrypt the disk, the password cannot have accents or the letter c-cedilla": "Om du krypterar disken kan lösenordet inte innehålla accenttecken eller bokstaven ç"
    },
    "tr": {
        "If you encrypt the disk, the password cannot have accents or the letter c-cedilla": "Diski şifrelerseniz, parola aksanlı harfler veya ç harfi içeremez"
    },
    "uk": {
        "If you encrypt the disk, the password cannot have accents or the letter c-cedilla": "Якщо ви зашифруєте диск, пароль не може містити символи з діакритикою або літеру ç"
    },
    "zh": {
        "If you encrypt the disk, the password cannot have accents or the letter c-cedilla": "如果加密磁盘，密码不能包含带重音符号的字符或字母 ç"
    },
    "pt": pt
}

function translate(source, localeKey) {
    var name = String(localeKey).split("|")[0].toLowerCase().replace("-", "_")
    var language = byLanguage[name] !== undefined ? name : name.split("_")[0]
    var catalog = byLanguage[language]
    if (catalog !== undefined && catalog[source] !== undefined) return catalog[source]
    return source
}
