# Retorno F3 (Elrond, instância nova) · fechamento-nuvem · base e4dbadd

Veredito: **quase pronto**. Código e testes da F3 verdes; a suíte inteira tem **3 falhas em 3 testes fora do escreva-só** (precisam de ajuste que a própria B15 impõe). Nada comitado (sem add, commit, stash nem checkout). Só dados sintéticos.

## Contagens
- `git diff --numstat -- S/` (linhas adicionadas): sc.py 8, sc_ciclo.py 38, sc_conferir.py 12, sc_registro.py 27, sc_rodada.py 53, sc_status.py 97 = **235** (teto da fatia, 800). Teste novo `T/test_aceite_nao_forjavel.py`: 23 testes. Testes antigos ajustados: dg02 (41/42), pacote2 (14/8), test_rodada (36/14), test_sc_rodada (19/10).
- Antes do código: o arquivo novo deu 18 falhas e 4 erros em 23 testes (o resto passava por controle). Depois: 23 OK.
- `python3 -B -m unittest tests.test_aceite_nao_forjavel tests.adversarial.test_dg02_aceite_forjavel`: 47 testes, OK.
- Suíte: `unittest discover -s tests`: 733 testes, 3 falhas (abaixo), 5 expectedFailure (todas do dg03, fora desta fatia), 1 skipped. `validar_pacote.py`: "pacote válido".

## O que mudou, por item
- B15 `decidir` (`sc_ciclo`): atestado precisa de `atestado_hash` conferido (`sc_status.hash_do_atestado_confere`); grava `atestado_hash` na decisão (`sc_registro.registrar_decisao`, parâmetro novo). (d) recusa como decisor o rótulo de papel, o nome de agente e o modelo de qualquer linha do perfil (`_nome_do_perfil`).
- B15 `sc_rodada`: `evidencia` EXECUTA o comando (sem shell, timeout) e grava o código e a saída medidos; saem `--exit-code` e `--saida`. `parecer` passa a ser `--arquivo` (lint; revisor, fornecedor, veredito, nível e critérios vêm do arquivo; implementador, do registro); saem `--veredito`, `--implementador`, `--revisor`, `--fornecedor`, `--criterio-ok/pendente`, `--nivel/justificativa-independencia`. `encerrar` exige `decisao_registrada` (aceitar, rejeitar ou sem-aceite), também com `--forcar`, e não encerra de novo etapa que o `decidir` já encerrou.
- (a) `sc_registro.registrar_parecer`: o fornecedor do perfil prevalece; declaração que o contradiz é recusada; o fornecedor declarado pelo revisor é conferido com o perfil. `sc.py revisar --implementador` ficou (agora conferido), por isso `test_ciclo.py` não precisou mudar.
- (b) e (c) `sc_status.verificar_aceite` (uso real, sem `registro=`): atestado no head com hash, forma 1.3.0 e perfil conferidos, igual ao `atestado_hash` da decisão; se o PR altera `.github/workflows/`, a ordem (hash da abertura conferido) precisa listar o caminho no escreva-só. **`.github/` não foi tocado**: o item (c) saiu em Python, sem pendência.
- B17b: `sc_conferir.atestado_aprovado` aplica hash + `forma_do_atestado` (recusa avulso e `--area` parcial). `sc.py revisar` sem `--parecer` usa o worktree da etapa e copia ordem, atestado e perfil para `sociedade/` da cópia (só o que falta; fica fora do git do revisor).
- Sondas DG-02: 8 sem `@expectedFailure`, reescritas para a interface nova, sem perder asserção. Não há sonda E3 em `T/adversarial` (o `grep` não achou); o E3 está coberto pelos testes B17b do arquivo novo.

## Pendências para o Círdan (escreva-só)
1. Três testes fora da lista usam atestado escrito à mão, que a B15 passa a recusar: `T/test_contrato_modelos.py::test_ordem_modelo_preenchida_nao_deixa_entrega_por_preencher`, `T/test_pipeline_v3.py::TestConferenciaDaOrdem::test_marca_feito_nao_feito_e_nao_preenchido`, `T/test_status.py::TestAceite::test_registro_lido_do_head_do_git`. Patch pronto e testado numa cópia (3 testes verdes), abaixo; falta ampliar o escreva-só e aplicar (`git apply` na raiz de `sociedade-do-codigo/`).
2. Limite do hash: sem segredo, quem lê o código recalcula o hash. A fórmula (`sc_pre_devolucao`, fora do escreva-só) não cobre `total_arquivos_inspecionados`; compensei exigindo total = nº de `hashes_artefatos`. Fechar de vez pede o `entregar` registrar o hash no registro (`sc.py entregar`, `sc_pre_devolucao`): sugiro B-nova.
3. `verificar_portao` (status `portao`) não confere o hash (os testes de `test_status` ainda usam atestado à mão); com o patch abaixo os fixtures já trazem hash, então dá para exigir depois.

## Atritos
- Escreva-só da subordem não previa os 3 testes acima (o `grep` só buscou os argumentos legados, não o uso de atestado à mão).
- `python3 -m unittest tests.test_rodada` falha com `No module named 'util'` (já era assim); só `unittest discover -s tests -p <arquivo>` roda esses arquivos soltos.

## Patch dos 3 testes (aplicar ao ampliar o escreva-só)
```diff
diff --git a/tests/test_contrato_modelos.py b/tests/test_contrato_modelos.py
index f15e2fc..ab518c0 100644
--- a/tests/test_contrato_modelos.py
+++ b/tests/test_contrato_modelos.py
@@ -11,6 +11,7 @@ Analisadores:
   ordem-modelo.md     -> sociedade-do-codigo/scripts/sc_conferir.py (bloco ```entregas)
   avaliacao-modelo.md -> nenhum script o lê (documento de orientação); ver SEM_ANALISADOR.
 """
+import hashlib
 import json
 import os
 import re
@@ -173,8 +174,17 @@ def repositorio_ordem(raiz):
     git(raiz, 'remote', 'add', 'origin', str(origem))
     git(raiz, 'push', '-q', 'origin', 'etapa/etapa-sintetica')
     (raiz / 'sociedade' / 'pareceres').mkdir(parents=True)
-    (raiz / 'sociedade' / 'pareceres' / 'atestado-etapa-sintetica.json').write_text(
-        json.dumps({'status': 'APROVADO', 'commit': final, 'total_arquivos_inspecionados': 1}), encoding='utf-8')
+    perfil = 'perfil sintético\n'
+    (raiz / 'sociedade' / 'perfil.md').write_text(perfil, encoding='utf-8')
+    at = {'status': 'APROVADO', 'commit': final, 'base': base, 'papel': 'Coordenador', 'etapa_id': 'etapa-sintetica', 'fatia_id': 'N/A',
+          'verificacoes': {}, 'erros': [], 'hashes_artefatos': {'src/x.py': 'a' * 64}, 'arquivos_inspecionados': ['src/x.py'],
+          'total_arquivos_inspecionados': 1,
+          'portao': {'modo': 'por_area', 'commit': final, 'perfil_sha256': hashlib.sha256(perfil.encode('utf-8')).hexdigest(),
+                     'areas_tocadas': ['p'], 'cobertura_completa': True, 'areas': [{'area': 'p', 'ok': True}]}}
+    at['atestado_hash'] = hashlib.sha256(json.dumps({k: at.get(k) for k in (
+        'commit', 'base', 'papel', 'etapa_id', 'fatia_id', 'status', 'verificacoes', 'hashes_artefatos', 'portao', 'erros')},
+        sort_keys=True).encode('utf-8')).hexdigest()  # B15: o atestado tem o hash que a conferência recalcula
+    (raiz / 'sociedade' / 'pareceres' / 'atestado-etapa-sintetica.json').write_text(json.dumps(at), encoding='utf-8')
     SHA_FINAL_BASE[:] = [base, final]
     return base, final
 
diff --git a/tests/test_pipeline_v3.py b/tests/test_pipeline_v3.py
index 3357bba..554b368 100644
--- a/tests/test_pipeline_v3.py
+++ b/tests/test_pipeline_v3.py
@@ -1,4 +1,5 @@
 """Ferramentas do pipeline 3.0.0: medição de sessão, conferência da ordem, estado, sc.py e validador."""
+import hashlib
 import json
 import subprocess
 import sys
@@ -136,7 +137,17 @@ class TestConferenciaDaOrdem(unittest.TestCase):
 
     def test_marca_feito_nao_feito_e_nao_preenchido(self):
         at = self.repo / 'sociedade' / 'pareceres' / 'atestado-E1.json'
-        at.write_text(json.dumps({'status': 'APROVADO', 'commit': self.head, 'total_arquivos_inspecionados': 1}), encoding='utf-8')
+        perfil = 'perfil sintético\n'
+        (self.repo / 'sociedade' / 'perfil.md').write_text(perfil, encoding='utf-8')
+        dados = {'status': 'APROVADO', 'commit': self.head, 'base': self.base, 'papel': 'Coordenador', 'etapa_id': 'E1',
+                 'fatia_id': 'N/A', 'verificacoes': {}, 'erros': [], 'hashes_artefatos': {'pacote/a.py': 'a' * 64},
+                 'arquivos_inspecionados': ['pacote/a.py'], 'total_arquivos_inspecionados': 1,
+                 'portao': {'modo': 'por_area', 'commit': self.head, 'areas_tocadas': ['p'], 'cobertura_completa': True,
+                            'perfil_sha256': hashlib.sha256(perfil.encode('utf-8')).hexdigest(), 'areas': [{'area': 'p', 'ok': True}]}}
+        dados['atestado_hash'] = hashlib.sha256(json.dumps({k: dados.get(k) for k in (
+            'commit', 'base', 'papel', 'etapa_id', 'fatia_id', 'status', 'verificacoes', 'hashes_artefatos', 'portao', 'erros')},
+            sort_keys=True).encode('utf-8')).hexdigest()  # B15: atestado do `entregar`: forma 1.3.0 e hash conferidos
+        at.write_text(json.dumps(dados), encoding='utf-8')
         vazio = self.repo / 'sociedade' / 'pareceres' / 'atestado-vazio.json'
         vazio.write_text(json.dumps({'status': 'APROVADO', 'commit': self.head, 'total_arquivos_inspecionados': 0}), encoding='utf-8')
         arq = self.ordem([
diff --git a/tests/test_status.py b/tests/test_status.py
index b040938..bcaf16f 100644
--- a/tests/test_status.py
+++ b/tests/test_status.py
@@ -32,6 +32,11 @@ def atestado(commit, **extra):
                        'perfil_sha256': hashlib.sha256(PERFIL_TEXTO.encode('utf-8')).hexdigest(),
                        'areas': [{'area': 'p', 'ok': True, 'testes': {'total': 1, 'pulados': 0, 'falhos': 0}}]}}
     base.update(extra)
+    # B15: o atestado do `entregar` traz o hash dos campos e os totais coerentes com `hashes_artefatos`
+    base.setdefault('hashes_artefatos', {'src/a.py': 'a' * 64})
+    base.setdefault('arquivos_inspecionados', sorted(base['hashes_artefatos']))
+    base['total_arquivos_inspecionados'] = len(base['hashes_artefatos']) if 'total_arquivos_inspecionados' not in extra else extra['total_arquivos_inspecionados']
+    base.setdefault('atestado_hash', sc_status.hash_do_atestado(base))
     return base
 
 
@@ -271,7 +276,8 @@ class TestAceite(Repo):
         pasta = self.r / 'sociedade'
         reg = Registro.inicializar(pasta, 'projeto-teste', str(self.r))
         reg.abrir_etapa(ETAPA, 'objetivo', 'plano', 'aut', self.base[:7], ['C1'])
-        evento = {'tipo': 'decisao_registrada', 'dados': decisao(commit=self.p)['dados']}
+        hash_do_atestado = json.loads((self.r / ATESTADO).read_text(encoding='utf-8'))['atestado_hash']
+        evento = {'tipo': 'decisao_registrada', 'dados': decisao(commit=self.p, atestado_hash=hash_do_atestado)['dados']}
         reg.aplicar_mutacao(lambda dados: [evento], autor='Odival Teste')
         head = self.commit({'sociedade/_marca': 'ok\n'}, 'sociedade: registro')
         r = sc_status.verificar_aceite(self.r, RAMO, head)
```
