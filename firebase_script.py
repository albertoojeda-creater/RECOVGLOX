from rich.console import Console, Group
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich import box
from rich.layout import Layout
from rich.align import Align
import firebase_admin
from firebase_admin import credentials, firestore
import serial
import time
import re
import threading
import os

console = Console()

# Firebase config
cred = credentials.Certificate(r"C:\Users\alber\Downloads\proyecto.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# Arduino serial
arduino = serial.Serial('COM3', 9600, timeout=1)
time.sleep(2)
arduino.flushInput()

# Traducción de dedos
finger_translation = {
    "índice": "Index",
    "medio": "Middle",
    "anular": "Ring",
    "meñique": "Little"
}

# Variables globales
servo_velocity = None
servo_force = None
USER_ID = None
SESSION_NUMBER = None

# Datos por dedo
dedo_data = {
    "Index": {},
    "Middle": {},
    "Ring": {},
    "Little": {}
}

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_session_collection_name():
    return "datos" if SESSION_NUMBER == 1 else f"datos{SESSION_NUMBER - 1}"

def send_data_to_firebase(dedo, angle, force, servoforce, velocity):
    try:
        dedo_en = finger_translation.get(dedo.lower(), dedo)
        session_collection = get_session_collection_name()
        ref = db.collection("usuarios").document(USER_ID).collection(session_collection).document(dedo_en)

        data = {
            "angle": float(angle),
            "force": float(force),
            "servoforce": float(servoforce),
            "velocity": float(velocity)
        }

        ref.set(data)
        dedo_data[dedo_en] = data
        draw_static_view()

    except Exception as e:
        console.print(f"[bold red]❌ Error al guardar en Firebase:[/] {e}")

def draw_static_view():
    clear()

    layout = Layout()
    layout.split(
        Layout(name="header", size=3),
        Layout(name="data", ratio=1),
        Layout(name="footer", size=1)
    )

    layout["header"].update(Align.center(
        f"[bold magenta]🦾 MONITOR DE DEDOS EN TIEMPO REAL\n[white]Usuario: [cyan]{USER_ID}[/] | Sesión: [green]{SESSION_NUMBER}[/]",
        vertical="middle"
    ))

    data_panels = []
    for dedo, data in dedo_data.items():
        if not data:
            continue
        table = Table.grid(expand=True)
        table.add_column("Dato", style="bold cyan", justify="center")
        table.add_column("Valor", style="bold white", justify="center")
        table.add_row("📐 Ángulo (°)", f"{data.get('angle', 'N/A')}")
        table.add_row("💪 Fuerza (N)", f"{data.get('force', 'N/A')}")
        table.add_row("⚙️ Fuerza Servo (N)", f"{data.get('servoforce', 'N/A')}")
        table.add_row("🚀 Velocidad", f"{data.get('velocity', 'N/A')}")
        panel = Panel(table, title=f"🖐️ {dedo}", box=box.ROUNDED, border_style="green")
        data_panels.append(panel)

    layout["data"].update(
        Align.center(
            Panel.fit(
                Group(*data_panels),
                title="📊 Datos de los Dedos",
                border_style="magenta"
            )
        )
    )

    layout["footer"].update(Align.center("[bold grey58]Presiona Ctrl+C para salir."))

    console.print(layout)

def mover_servo(comando):
    if comando.upper() in ['L', 'R', 'S']:
        arduino.write(f"{comando.upper()}\n".encode())
        console.print(f"[cyan]📤 Comando enviado:[/] {comando.upper()}")
    else:
        console.print("[red]❗ Comando inválido. Usa 'L', 'R' o 'S'.")

def leer_serial():
    global servo_velocity, servo_force
    buffer_line = ""  # para guardar fuerza luego del ángulo
    while True:
        if arduino.in_waiting > 0:
            recibido = arduino.readline().decode(errors='ignore').strip()

            if not recibido:
                continue  # Ignorar líneas vacías

            # Captura de velocidad del servo
            if "Girando" in recibido and "a velocidad" in recibido:
                match = re.search(r"Girando a la (izquierda|derecha) a velocidad: (\d+)", recibido)
                if match:
                    servo_velocity = match.group(2)

            # Captura de fuerza generada por el servo
            elif "Fuerza generada por el servo:" in recibido:
                match = re.search(r"Fuerza generada por el servo: ([\d.]+) N", recibido)
                if match:
                    servo_force = match.group(1)

            # Captura de datos de dedo
            elif "Dedo" in recibido and "Ángulo" in recibido:
                match = re.match(r"Dedo (\w+) - Voltaje: [\d.]+ V \| Ángulo: ([\d.]+) grados", recibido)
                if match:
                    dedo = match.group(1).strip()
                    angle = match.group(2).strip()

                    # Lee siguiente línea esperando la fuerza del dedo
                    if arduino.in_waiting > 0:
                        buffer_line = arduino.readline().decode(errors='ignore').strip()
                        force_match = re.match(r"Fuerza ejercida por el dedo: ([\d.]+) N", buffer_line)
                        if force_match:
                            force = force_match.group(1).strip()
                            # Validar que servo_force y servo_velocity no sean None
                            fuerza_servo = servo_force if servo_force is not None else 0.0
                            velocidad_servo = servo_velocity if servo_velocity is not None else 0
                            send_data_to_firebase(dedo, angle, force, fuerza_servo, velocidad_servo)


def pedir_id_usuario():
    global USER_ID, SESSION_NUMBER
    USER_ID = Prompt.ask("[bold blue]🔑 Ingresa el ID del usuario en Firebase")

    while True:
        session_input = Prompt.ask("[bold green]📋 Ingresa el número de la sesión (1, 2, 3, ...)")
        if session_input.isdigit() and int(session_input) >= 1:
            SESSION_NUMBER = int(session_input)
            break
        else:
            console.print("[red]❗ Entrada inválida. Ingresa un número de sesión válido (1 o mayor).")

def mostrar_comandos():
    console.print(Panel.fit(
        "🛠️ [bold magenta]Control del Servo[/bold magenta]\n\n"
        "[green]L[/]: Izquierda  │  [yellow]R[/]: Derecha  │  [red]S[/]: Stop",
        style="bold blue",
        subtitle="👉 Escribe un comando para mover el servo"
    ))

def main():
    pedir_id_usuario()
    threading.Thread(target=leer_serial, daemon=True).start()

    while True:
        mostrar_comandos()
        comando = Prompt.ask("[bold blue]✏️ Comando (L/R/S)")
        mover_servo(comando)

# Ejecutar
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[bold red]👋 Programa detenido por el usuario.[/]")