"""CLI interface for CameraBlur using Typer."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .config import AppConfig, EffectMode, RVMModel, SegmentationBackend, load_config
from .exceptions import CameraBlurError
from .pipeline import run_pipeline
from .utils.system_check import check_system_requirements, get_real_cameras, list_cameras

app = typer.Typer(
    name="camerablur",
    help="Linux virtual camera with AI-powered background blur and replacement",
    no_args_is_help=True,
)
console = Console()


@app.command()
def run(
    config_file: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to configuration file",
    ),
    camera: Optional[int] = typer.Option(
        None,
        "--camera",
        "-d",
        help="Camera device ID",
    ),
    blur: Optional[int] = typer.Option(
        None,
        "--blur",
        "-b",
        help="Blur intensity (odd number, e.g., 21)",
    ),
    background: Optional[Path] = typer.Option(
        None,
        "--background",
        "-bg",
        help="Background image or video path",
    ),
    preview: bool = typer.Option(
        False,
        "--preview",
        "-p",
        help="Show preview window",
    ),
    gpu: bool = typer.Option(
        True,
        "--gpu/--no-gpu",
        help="Enable GPU acceleration (RVM) or use CPU (MediaPipe)",
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        "-m",
        help="RVM model variant: mobilenetv3 (fast) or resnet50 (quality)",
    ),
) -> None:
    """Start the virtual camera with background effects."""
    try:
        config = load_config(config_file)

        if camera is not None:
            config.camera.device_id = camera

        if blur is not None:
            config.effect.mode = EffectMode.BLUR
            config.effect.blur_intensity = blur if blur % 2 == 1 else blur + 1

        if background is not None:
            if not background.exists():
                console.print(f"[red]Background file not found: {background}[/red]")
                raise typer.Exit(1)

            suffix = background.suffix.lower()
            if suffix in {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif"}:
                config.effect.mode = EffectMode.IMAGE
            else:
                config.effect.mode = EffectMode.VIDEO
            config.effect.background_path = background

        if preview:
            config.debug.preview_window = True

        # Handle GPU/segmentation backend
        if gpu:
            config.segmentation.backend = SegmentationBackend.RVM
            if model is not None:
                try:
                    config.segmentation.rvm_model = RVMModel(model.lower())
                except ValueError:
                    console.print(f"[red]Invalid model: {model}. Use 'mobilenetv3' or 'resnet50'[/red]")
                    raise typer.Exit(1)
        else:
            config.segmentation.backend = SegmentationBackend.MEDIAPIPE

        console.print("[bold blue]CameraBlur[/bold blue] starting...")
        console.print(f"  Camera: device {config.camera.device_id}")
        console.print(f"  Resolution: {config.camera.width}x{config.camera.height}")
        if config.segmentation.backend == SegmentationBackend.RVM:
            console.print(f"  Segmentation: RVM ({config.segmentation.rvm_model.value}) [GPU]")
        else:
            console.print(f"  Segmentation: MediaPipe [CPU]")
        console.print(f"  Effect: {config.effect.mode.value}")
        if config.effect.mode == EffectMode.BLUR:
            console.print(f"  Blur intensity: {config.effect.blur_intensity}")
        elif config.effect.background_path:
            console.print(f"  Background: {config.effect.background_path}")
        console.print()

        run_pipeline(config)

    except CameraBlurError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/yellow]")


@app.command("list-devices")
def list_devices() -> None:
    """List available camera devices."""
    cameras = list_cameras()

    if not cameras:
        console.print("[yellow]No camera devices found[/yellow]")
        return

    table = Table(title="Camera Devices")
    table.add_column("ID", style="cyan")
    table.add_column("Device", style="green")
    table.add_column("Name")
    table.add_column("Type", style="magenta")

    for cam in cameras:
        cam_type = "Virtual" if cam.is_virtual else "Physical"
        table.add_row(
            str(cam.device_id),
            cam.device_path,
            cam.name,
            cam_type,
        )

    console.print(table)

    real_cams = [c for c in cameras if not c.is_virtual]
    virtual_cams = [c for c in cameras if c.is_virtual]

    console.print()
    if real_cams:
        console.print(f"[green]Physical cameras available: {len(real_cams)}[/green]")
    else:
        console.print("[yellow]No physical cameras found[/yellow]")

    if virtual_cams:
        console.print(f"[green]Virtual cameras available: {len(virtual_cams)}[/green]")
    else:
        console.print("[yellow]No virtual cameras found. Run: sudo modprobe v4l2loopback[/yellow]")


@app.command()
def check() -> None:
    """Check system requirements for CameraBlur."""
    console.print("[bold]System Requirements Check[/bold]\n")

    results = check_system_requirements()

    table = Table()
    table.add_column("Requirement", style="cyan")
    table.add_column("Status")

    status_icon = lambda ok: "[green]OK[/green]" if ok else "[red]MISSING[/red]"

    table.add_row(
        "v4l2loopback kernel module",
        status_icon(results["v4l2loopback_loaded"]),
    )
    table.add_row(
        "Virtual camera device",
        status_icon(results["virtual_camera_available"]),
    )
    table.add_row(
        "Physical camera",
        status_icon(results["real_camera_available"]),
    )

    console.print(table)
    console.print()

    all_ok = all(results.values())

    if all_ok:
        console.print("[green]All requirements met! You can run: camerablur run[/green]")
    else:
        console.print("[yellow]Some requirements are missing:[/yellow]")

        if not results["v4l2loopback_loaded"]:
            console.print("  - Load v4l2loopback: [cyan]sudo modprobe v4l2loopback devices=1 card_label='VirtualCam'[/cyan]")
            console.print("  - For persistence, add to /etc/modules-load.d/")

        if not results["virtual_camera_available"] and results["v4l2loopback_loaded"]:
            console.print("  - Create virtual camera: [cyan]sudo modprobe -r v4l2loopback && sudo modprobe v4l2loopback devices=1[/cyan]")

        if not results["real_camera_available"]:
            console.print("  - Connect a webcam to your computer")


@app.command()
def tui(
    config_file: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to configuration file",
    ),
    preview: bool = typer.Option(
        False,
        "--preview",
        "-p",
        help="Also show OpenCV preview window",
    ),
) -> None:
    """Launch interactive TUI for controlling CameraBlur."""
    try:
        config = load_config(config_file)
        if preview:
            config.debug.preview_window = True

        from .tui import CameraBlurTUI

        tui_app = CameraBlurTUI(config, config_path=config_file)
        tui_app.run()

    except CameraBlurError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/yellow]")


if __name__ == "__main__":
    app()
