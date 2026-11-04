# Como contribuir

Toda modificação passa por uma issue, uma branch de trabalho e um pull request (PR). A `main` é a branch de integração e a fonte publicada pelo GitHub Pages.

## 1. Registre a issue

Antes de alterar arquivos, localize uma issue que já cubra a mudança ou abra uma nova. Registre o contexto, o resultado esperado e como verificar a entrega.

## 2. Crie a branch

Parta da `main` atualizada e use o formato `<tipo>/<resumo>-issue-<numero>`. Escreva o resumo em minúsculas, com palavras separadas por hífens, e use o número da issue principal.

| Tipo | Quando usar | Exemplo |
| --- | --- | --- |
| `doc` | Documentação, guias ou explicações | `doc/documentar-fluxo-de-contribuicao-issue-3` |
| `chore` | Manutenção, dependências ou organização do repositório | `chore/atualizar-dependencias-issue-41` |
| `feature` | Nova funcionalidade | `feature/filtrar-fragmentos-issue-42` |
| `bugfix` | Correção de um comportamento incorreto | `bugfix/corrigir-legenda-do-mapa-issue-43` |

Crie a branch pela seção **Development** da issue para vinculá-la no GitHub. Se usar o GitHub CLI, o comando `gh issue develop` faz o mesmo vínculo. Mantenha os commits no escopo da issue. [Criar uma branch para uma issue](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/creating-a-branch-for-an-issue)

## 3. Abra o pull request

Abra um PR da branch de trabalho para a `main` com um título que descreva a mudança. Preencha o [modelo de PR](.github/pull_request_template.md).

- **Issue associada** — use `Closes #N` se o PR concluir a issue ou `Refs #N` se fizer parte da entrega. O GitHub fecha automaticamente a issue indicada por `Closes` quando o PR entra na `main`. [Vincular um PR a uma issue](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue)
- **Contexto** — explique o problema ou a necessidade que motivou a mudança.
- **Comportamento esperado** — diga o que deve acontecer após a integração.
- **Descrição técnica** — descreva o que mudou e como a solução foi implementada.
- **Validação** — informe como a mudança foi verificada e inclua passos para reproduzir a verificação quando necessário.

Em mudanças de metodologia, indique as camadas, os critérios e os campos afetados. Em mudanças no mapa, indique como testar o comportamento e a origem de qualquer dado acrescentado.

## 4. Revise e integre

Revise o diff, resolva os comentários e confirme as verificações aplicáveis antes de mesclar o PR. Após o merge, confira o resultado na `main` e o estado da issue. Se o PR concluir apenas parte do trabalho, registre o que falta na issue.

As contribuições seguem o [código de conduta](CODE_OF_CONDUCT.md).
