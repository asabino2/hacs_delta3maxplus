# EcoFlow Delta 3 Max Plus (HACS)

Integracao customizada para Home Assistant via HACS para controle e telemetria EcoFlow, sem depender de servidor intermediario.

## O que faz

- Configuracao em 2 etapas:
  - Entrada de `application key` e `secret`.
  - Selecao de inversores (SN) disponiveis na conta com selecao multipla.
- Cria sensores para todos os campos mapeados da telemetria.
- Adiciona servicos para desligar AC1 e AC2.

## Instalacao

1. Copie este repositorio para o seu caminho de `custom_repository` do HACS.
2. Instale a integracao pelo HACS.
3. Reinicie o Home Assistant.
4. Em **Configuracoes > Dispositivos e Servicos**, adicione **EcoFlow Delta 3 Max Plus**.

## Servicos

- `ecoflow_delta3_max_plus.turn_off_ac1`
- `ecoflow_delta3_max_plus.turn_off_ac2`

Ambos aceitam `sn` opcional. Se omitido, o servico aplica a todos os inversores configurados.
