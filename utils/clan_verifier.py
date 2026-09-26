"""
utils/clan_verifier.py — Lógica de validação de entradas de jogadores no clã.
"""

def verify_clan_entries(expected_count: int, detected_data: dict) -> dict:
    """
    Compara a quantidade esperada com a quantidade detectada pela IA e formata o resultado.
    
    Retorna um dicionário com os seguintes campos:
    - 'coincide': bool (indica se as quantidades batem)
    - 'status_text': str (resumo da validação)
    - 'status_color': int (cor hexadecimal para o Embed do Discord)
    - 'total_detectado': int
    - 'jogadores': list
    - 'mensagem_detalhe': str (descrição detalhada das diferenças)
    """
    jogadores = detected_data.get("jogadores", [])
    total_detectado = detected_data.get("total_encontrado", 0)
    
    # Normalização preventiva se o Gemini retornar inconsistência entre o total declarado e o tamanho da lista
    if len(jogadores) != total_detectado:
        total_detectado = len(jogadores)

    coincide = total_detectado == expected_count
    
    if coincide:
        status_text = "✅ Validação Concluída: Coincide!"
        status_color = 0x2ecc71  # Verde
        mensagem_detalhe = f"Todos os {expected_count} jogadores esperados foram detectados com sucesso na imagem."
    else:
        status_text = "⚠️ Divergência Detectada!"
        status_color = 0xe74c3c  # Vermelho
        diferenca = abs(total_detectado - expected_count)
        if total_detectado > expected_count:
            mensagem_detalhe = (
                f"Foram detectados **{total_detectado}** jogadores na imagem, mas o esperado era **{expected_count}**.\n"
                f"Há **{diferenca}** jogador(es) a mais do que o informado."
            )
        else:
            mensagem_detalhe = (
                f"Foram detectados **{total_detectado}** jogadores na imagem, mas o esperado era **{expected_count}**.\n"
                f"Faltam **{diferenca}** jogador(es) na imagem em relação ao informado."
            )

    return {
        "coincide": coincide,
        "status_text": status_text,
        "status_color": status_color,
        "total_detectado": total_detectado,
        "jogadores": jogadores,
        "mensagem_detalhe": mensagem_detalhe
    }
