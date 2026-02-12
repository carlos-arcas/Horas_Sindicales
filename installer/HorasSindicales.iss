[Setup]
AppId={{F46CF76E-BD81-4865-B4B9-A6BB4F88F0A4}
AppName=Horas Sindicales
AppVersion=0.1.0
AppPublisher=Horas Sindicales
DefaultDirName={autopf}\Horas Sindicales
DefaultGroupName=Horas Sindicales
DisableProgramGroupPage=yes
OutputDir=output
OutputBaseFilename=HorasSindicalesSetup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\HorasSindicales.exe
SetupIconFile=..\cgt_reservar_horas_sindicales.ico

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el Escritorio"; GroupDescription: "Iconos adicionales:"; Flags: unchecked

[Files]
Source: "..\dist\HorasSindicales\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Horas Sindicales"; Filename: "{app}\HorasSindicales.exe"; IconFilename: "{app}\cgt_reservar_horas_sindicales.ico"
Name: "{autodesktop}\Horas Sindicales"; Filename: "{app}\HorasSindicales.exe"; Tasks: desktopicon; IconFilename: "{app}\cgt_reservar_horas_sindicales.ico"

[Run]
Filename: "{app}\HorasSindicales.exe"; Description: "Iniciar Horas Sindicales"; Flags: nowait postinstall skipifsilent
