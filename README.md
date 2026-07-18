# EcoFlow Delta 3 Max Plus (HACS)

Integracao customizada para Home Assistant via HACS para controle e telemetria EcoFlow, sem depender de servidor intermediario.

## O que faz

- Configuracao em 2 etapas:
  - Entrada de `application key` e `secret`.
  - Selecao de inversores (SN) disponiveis na conta com selecao multipla.
- Cria sensores para todos os campos mapeados da telemetria.
- Cria switches para AC1, AC2 e um switch mestre AC1+AC2 por inversor.
- Adiciona servicos para ligar/desligar AC1, AC2 e AC1+AC2 juntos.

## Instalacao

1. Copie este repositorio para o seu caminho de `custom_repository` do HACS.
2. Instale a integracao pelo HACS.
3. Reinicie o Home Assistant.
4. Em **Configuracoes > Dispositivos e Servicos**, adicione **EcoFlow Delta 3 Max Plus**.

## Servicos

- `ecoflow_delta3_max_plus.turn_on_ac1`
- `ecoflow_delta3_max_plus.turn_off_ac1`
- `ecoflow_delta3_max_plus.turn_on_ac2`
- `ecoflow_delta3_max_plus.turn_off_ac2`
- `ecoflow_delta3_max_plus.turn_on_all_ac`
- `ecoflow_delta3_max_plus.turn_off_all_ac`

Ambos aceitam `sn` opcional. Se omitido, o servico aplica a todos os inversores configurados.

## Changelog

### 0.1.8
- Adicionado botao de configuracao da integracao (Configure) para alterar intervalo de atualizacao.
- Novas opcoes com selecao: `Default Scan Interval` (usa `DEFAULT_SCAN_INTERVAL`) ou `Custom` com campo numerico em segundos.
- Alteracao de opcoes agora recarrega automaticamente a integracao para aplicar o novo intervalo.
- Campo numerico de intervalo exibido na mesma tela das opcoes de modo para facilitar o preenchimento.

### 0.1.7
- Sensores de potencia passaram a usar valores absolutos (sempre positivos), incluindo AC input/output, total output, total input e USB-C power.

### 0.1.6
- Adicionado sensor `X-Boost` baseado na tag `xboostEn` (true=ligado, false=desligado).
- Switch `X-Boost` agora usa fallback para o valor de `xboostEn`, refletindo melhor o estado real no dashboard.

### 0.1.5
- Corrigida a reflexao de estado dos switches AC1, AC2 e 12v no dashboard usando fallback por `flowInfo*` quando `cfg*` nao vier no payload.

### 0.1.4
- Adicionados 3 sensores de status: `AC1 Out Status`, `AC2 Out Status` e `12v Out Status`.
- Regra aplicada: status `off` quando `flowInfo*` for `4`, caso contrario `on`.

### 0.1.3
- Adicionados novos switches por inversor: `DC12v Outlet`, `Energy Backup`, `Buzzer` e `X-Boost`.
- Implementado envio de comando `quota` generico para suportar payloads customizados desses switches.

### 0.1.2
- Adicionado switch mestre AC1+AC2 por inversor para ligar/desligar os dois canais juntos.
- Adicionados servicos `turn_on_all_ac` e `turn_off_all_ac`.

### 0.1.1
- Ajustes de compatibilidade e robustez do fluxo de configuracao e servicos.
