import argparse
import csv
import os
from collections import defaultdict
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "results/matplotlib-cache")

import matplotlib.pyplot as plt


GRAFICOS = [
    ("wall_seconds", "Tempo medio real por operacao", "Segundos", "tempo_operacao.png"),
    ("throughput_mb_s", "Vazao media real por operacao", "MB/s", "vazao_operacao.png"),
    ("system_cpu_seconds_per_gib", "Custo medio de CPU do sistema por GiB", "CPU-s/GiB", "cpu_operacao.png"),
]

OPERACOES = {
    "write": "Escrita",
    "read": "Leitura",
}


def ler_resultados(caminho_csv):
    with caminho_csv.open(newline="", encoding="utf-8") as arquivo:
        return list(csv.DictReader(arquivo))


def listar_cenarios(resultados):
    return list(dict.fromkeys(linha["scenario"] for linha in resultados))


def calcular_medias(resultados, campo):
    valores = defaultdict(list)

    for linha in resultados:
        chave = (linha["scenario"], linha["operation"])
        valores[chave].append(float(linha[campo]))

    return {chave: sum(lista) / len(lista) for chave, lista in valores.items()}


def gerar_grafico(resultados, campo, titulo, eixo_y, caminho_saida):
    cenarios = listar_cenarios(resultados)
    medias = calcular_medias(resultados, campo)
    posicoes = range(len(cenarios))
    largura = 0.36

    figura, eixo = plt.subplots(figsize=(10, 5))

    for indice, (operacao, rotulo) in enumerate(OPERACOES.items()):
        deslocamento = (indice - 0.5) * largura
        barras = [posicao + deslocamento for posicao in posicoes]
        alturas = [medias.get((cenario, operacao), 0) for cenario in cenarios]
        eixo.bar(barras, alturas, width=largura, label=rotulo)

    eixo.set_title(titulo)
    eixo.set_ylabel(eixo_y)
    eixo.set_xticks(list(posicoes))
    eixo.set_xticklabels(cenarios, rotation=15, ha="right")
    eixo.legend()
    eixo.grid(axis="y", linestyle="--", alpha=0.35)

    figura.tight_layout()
    figura.savefig(caminho_saida, dpi=140)
    plt.close(figura)


def gerar_graficos(caminho_csv, pasta_saida):
    resultados = ler_resultados(caminho_csv)

    if not resultados:
        raise ValueError("CSV sem resultados.")

    pasta_saida.mkdir(parents=True, exist_ok=True)

    for campo, titulo, eixo_y, arquivo in GRAFICOS:
        gerar_grafico(resultados, campo, titulo, eixo_y, pasta_saida / arquivo)


def criar_parser():
    parser = argparse.ArgumentParser(description="Gera graficos a partir do CSV do benchmark.")
    parser.add_argument("--input", type=Path, default=Path("results/benchmark.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("results/graficos"))
    return parser


def main():
    args = criar_parser().parse_args()
    gerar_graficos(args.input, args.output_dir)
    print(f"Graficos salvos em: {args.output_dir}")


if __name__ == "__main__":
    main()
