"""Regras de negócio (puras, fáceis de testar)."""


def pode_contribuir(usuario, disciplina):
    """Quem pode publicar resumo/avaliar? -> (bool, motivo).

    Regra (hipótese validada com o Bruno): o aluno só contribui em disciplinas cujo semestre ideal
    já passou, calculado pelo semestre de ingresso. Optativas (sem semestre) ficam liberadas e
    dependem da moderação. Moderadores e admins sempre podem.
    """
    if not usuario.is_authenticated:
        return False, "Entre com seu e-mail @usp.br para contribuir."
    if usuario.e_moderador:
        return True, ""
    if not usuario.perfil_completo:
        return False, "Complete seu perfil (ano e semestre de ingresso) para contribuir."
    if disciplina.semestre_ideal is None:
        return True, ""
    atual = usuario.semestre_no_curso()
    if atual is not None and atual > disciplina.semestre_ideal:
        return True, ""
    return False, (f"Esta disciplina é do {disciplina.semestre_ideal}º semestre e você está no {atual}º. "
                   "Só quem já passou por ela pode contribuir.")


def classe_dificuldade(media):
    if media is None:
        return ""
    if media < 2.5:
        return "baixa"
    if media <= 3.5:
        return "media"
    return "alta"
