import argparse
import csv
import os
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path


CAMPOS_CSV = [
    "timestamp",
    "scenario",
    "target",
    "iteration",
    "operation",
    "io_mode",
    "bytes",
    "wall_seconds",
    "throughput_mb_s",
    "system_cpu_seconds",
    "system_cpu_percent",
    "system_cpu_seconds_per_gib",
]


def tempos_cpu_sistema():
    with open("/proc/stat", encoding="utf-8") as arquivo:
        valores = [int(parte) for parte in arquivo.readline().split()[1:]]

    idle = valores[3] + valores[4]
    total = sum(valores)
    return idle, total


def executar_medido(comando, tamanho_mb, bytes_total):
    sistema_idle_inicio, sistema_total_inicio = tempos_cpu_sistema()
    parede_inicio = time.perf_counter()

    with tempfile.TemporaryFile() as erro_arquivo:
        processo = subprocess.Popen(comando, stdout=subprocess.DEVNULL, stderr=erro_arquivo)
        _, status, uso = os.wait4(processo.pid, 0)
        tempo_parede = time.perf_counter() - parede_inicio

        erro_arquivo.seek(0)
        erro_texto = erro_arquivo.read().decode("utf-8", errors="replace").strip()

    sistema_idle_fim, sistema_total_fim = tempos_cpu_sistema()
    codigo_saida = os.waitstatus_to_exitcode(status)

    if codigo_saida != 0:
        comando_texto = " ".join(comando)
        raise RuntimeError(f"Comando falhou ({codigo_saida}): {comando_texto}\n{erro_texto}")

    sistema_total_delta = sistema_total_fim - sistema_total_inicio
    sistema_idle_delta = sistema_idle_fim - sistema_idle_inicio
    sistema_ocupado_delta = sistema_total_delta - sistema_idle_delta

    clock_ticks = os.sysconf(os.sysconf_names["SC_CLK_TCK"])
    cpu_sistema = sistema_ocupado_delta / clock_ticks if clock_ticks > 0 else 0
    cpu_sistema_percentual = sistema_ocupado_delta / sistema_total_delta * 100 if sistema_total_delta > 0 else 0

    vazao_mb_s = tamanho_mb / tempo_parede if tempo_parede > 0 else 0
    gib = bytes_total / 1024 / 1024 / 1024

    return {
        "wall_seconds": tempo_parede,
        "throughput_mb_s": vazao_mb_s,
        "system_cpu_seconds": cpu_sistema,
        "system_cpu_percent": cpu_sistema_percentual,
        "system_cpu_seconds_per_gib": cpu_sistema / gib if gib > 0 else 0,
    }


def adicionar_linha(caminho_saida, linha):
    caminho_saida.parent.mkdir(parents=True, exist_ok=True)
    existe = caminho_saida.exists()

    with caminho_saida.open("a", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=CAMPOS_CSV)

        if not existe:
            escritor.writeheader()

        escritor.writerow(linha)


def salvar_resultado(args, iteracao, operacao, bytes_total, metricas):
    adicionar_linha(
        args.output,
        {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "scenario": args.scenario,
            "target": str(args.target),
            "iteration": iteracao,
            "operation": operacao,
            "io_mode": "direct",
            "bytes": bytes_total,
            "wall_seconds": f"{metricas['wall_seconds']:.6f}",
            "throughput_mb_s": f"{metricas['throughput_mb_s']:.2f}",
            "system_cpu_seconds": f"{metricas['system_cpu_seconds']:.6f}",
            "system_cpu_percent": f"{metricas['system_cpu_percent']:.2f}",
            "system_cpu_seconds_per_gib": f"{metricas['system_cpu_seconds_per_gib']:.6f}",
        },
    )


def executar_benchmark(args):
    blocos = args.file_size_mb // args.block_mb
    bytes_total = args.file_size_mb * 1024 * 1024

    for iteracao in range(1, args.iterations + 1):
        caminho_arquivo = args.target / f"benchmark_{os.getpid()}_{iteracao}.bin"

        comando_escrita = [
            "dd",
            "if=/dev/zero",
            f"of={caminho_arquivo}",
            f"bs={args.block_mb}M",
            f"count={blocos}",
            "oflag=direct",
            "conv=fdatasync",
            "status=none",
        ]
        metricas_escrita = executar_medido(comando_escrita, args.file_size_mb, bytes_total)
        salvar_resultado(args, iteracao, "write", bytes_total, metricas_escrita)

        comando_leitura = [
            "dd",
            f"if={caminho_arquivo}",
            "of=/dev/null",
            f"bs={args.block_mb}M",
            f"count={blocos}",
            "iflag=direct",
            "status=none",
        ]
        metricas_leitura = executar_medido(comando_leitura, args.file_size_mb, bytes_total)
        salvar_resultado(args, iteracao, "read", bytes_total, metricas_leitura)

        caminho_arquivo.unlink(missing_ok=True)


def criar_parser():
    parser = argparse.ArgumentParser(description="Mede leitura/escrita real com dd e I/O direto.")
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--file-size-mb", required=True, type=int)
    parser.add_argument("--iterations", required=True, type=int)
    parser.add_argument("--block-mb", required=True, type=int)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def main():
    args = criar_parser().parse_args()
    executar_benchmark(args)


if __name__ == "__main__":
    main()
