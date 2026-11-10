# Resistência do termossifão: controlo automático com overrides

Estado: rascunho para aprovação. Nada foi implementado.

## Intenção

O termossifão solar aquece sozinho em dias de sol. A resistência (2 kW, switch Shelly) serve de apoio. Hoje é ligada e
desligada à mão, porque a automação existente (`automations/temperature_and_humidity/control_hot_water_schedule.yaml`)
está desligada no HA desde Maio (último disparo: 19 Mai 2026) e porque não tem em conta o sol, faz ciclos curtos e
nunca apanha o excedente quando ele faz falta.

Objetivo: água com conforto nas duas janelas de banho, com o mínimo de energia da rede, sem ninguém ter de pensar na
resistência, e com botões de override que a automação nunca reverte.

## Objetivos

- No início de cada janela de banho a água está acima do mínimo de conforto: 55 ºC fora do Verão, 50 ºC no Verão
  (Verão = 1 Jun a 30 Set).
- Janelas de banho: segunda a sexta 07:00-09:00 e 19:30-21:30; sábado 09:00-13:00 (aproximado) e 19:30-21:30; domingo só
  19:30-21:30 (sem janela de manhã). A manhã de segunda é preparada a partir de domingo à noite, via `next_event`.
- Energia da rede só quando o sol não chega. O excedente solar é aproveitado quando a água tem margem para ele.
- Cada ciclo da resistência dura pelo menos 45 min ligado e 45 min desligado.
- Override por botões num dashboard novo, com reposição automática 2 vezes por dia (10:00 e 23:00; escolha minha).

## Não-objetivos

- Não medir o consumo real da resistência. O sensor de potência do Shelly não é fiável e o do powercalc assume 2000 W
  sempre que o switch está ligado (o termóstato corta a ~63-65 ºC), por isso sobrestima o consumo em várias vezes.
- Não usar previsão solar na fase 1 (ver "Fase 2").
- Não tocar nos scripts `mode_*` nem no `input_text.active_mode`.
- Não existe modo "Verão" separado: só os dois mínimos de conforto mudam com a data.

## Anti-objetivos (falha mesmo que "funcione")

- Resistência a ligar e desligar em minutos.
- Reverter um override do utilizador.
- Aquecer pela rede em dias de sol só para chegar a um número alto.
- Deixar a resistência ligada depois de a água estar na temperatura-alvo (o termóstato volta a armar quando a água
  arrefece e consome sem que a automação o tenha decidido).

## Evidência (dados do HA, 4 Mai a 10 Nov 2026)

- Com a resistência ligada a água estabiliza em 63-65 ºC (termóstato). Só o sol passa disso (até 92 ºC no Verão).
- Aquecimento medido: 6 a 10 ºC/h (44 para 63 ºC em ~2 h a 8 Nov, de noite). De 55 para 63 ºC demora ~1 h.
- Perdas em repouso: ~0,25 ºC/h a 43 ºC, ~0,7 ºC/h a 55-60 ºC no Outono; ~0,5 ºC/h a 55-60 ºC no Verão (exterior ~22 ºC).
- Dia de sol (pico de produção solar acima de 3,4 kW): o termossifão sobe 15 a 22 ºC até às 15h sozinho (4 Nov: 44 para
  66 ºC). Dia nublado: sem ganho e a água só desce (8 Nov).
- A exportação nos dias nublados foi no máximo 0,5 kW (6 e 10 Nov): a regra antiga "exporta mais de 2 kW" só disparava em
  dias de sol, quando a resistência já não fazia falta.
- Banho: queda de 4 a 16 ºC por hora na média horária.
- Pior semana de Verão (22 a 28 Jun, resistência 2,4 h): noite sempre 55 a 68 ºC às 19h; manhã 40 a 49 ºC às 7h em 5 de 7
  dias. A manhã é a janela crítica.
- Horas de resistência ligada por semana (estimativa do powercalc): ~0 de Junho a Agosto e em Setembro; 31 a 109 desde
  28 Set. A produção solar caiu de ~175 kWh/semana (Verão) para 108 kWh (semana de 2 Nov).
- Mínimo diário da água (35 a 42 ºC) não serve de métrica de conforto: aparece em todas as estações, mesmo com a
  resistência ligada, porque é o dip depois do banho. A métrica é a temperatura no início da janela.
- O Shelly fica `unavailable` ~0,2 s dezenas de vezes por mês e volta ao estado anterior. Isto repõe o `last_changed`.

## Entidades usadas

| Entidade | Papel |
|---|---|
| `switch.resistencia_termoacumulador_switch_0` | a resistência (só liga/desliga) |
| `sensor.hot_water_temperature` | temperatura da água (ºC) |
| `schedule.hotwater_schedule` | janelas de banho; o atributo `next_event` dá o próximo arranque/fim |
| `input_number.desired_hot_water_temperature_winter` | mínimo de conforto de 1 Out a 31 Mai (55); é o atual `desired_hot_water_temperature`, renomeado |
| `sensor.energy_consumption_mean_over_last_10_minutes` | W, média de 10 min da rede; negativo = exportar |

## Lógica de controlo (fase 1)

Uma única automação, `mode: single`, avalia o estado desejado e aplica-o. Dispara: de 5 em 5 min, na mudança do
override, e no início/fim das janelas. Ignora transições do switch de/para `unavailable`.

Constantes (num bloco `variables:` no topo, não em helpers): ritmo de aquecimento 6 ºC/h; perda 0,6 ºC/h; margem de
arranque 1,25; margem do alvo +5 ºC; paragem do excedente com importação média acima de 500 W.

Prioridade:

1. Override `Desligada`: desliga já (ignora o ciclo mínimo).
2. Override `Ligada`: liga já e não desliga automaticamente (decisão do utilizador; o termóstato protege).
3. `Auto`:
   - **Mínimo** M = `desired_hot_water_temperature_winter` (55), ou `desired_hot_water_temperature_summer` (50) de
     1 Jun a 30 Set.
     **Alvo** A = M + 5.
   - **Pronta a horas.** Seja W o início da próxima janela (`schedule.hotwater_schedule.next_event` quando o horário
     está `off`; "agora" se estiver `on`), T a temperatura atual, h = W − agora (horas).
     Liga se T − 0,6·h < M **e** h ≤ 1,25·(A − T)/6. Uma vez ligada por esta razão, só desliga quando T ≥ A.
     (Exemplo: 04:00, T = 47, Verão, W = 07:00: precisa de 1,7 h, arranca às ~05:20.)
     Dentro da janela, se T < M também liga e desliga em T ≥ A.
   - **Excedente.** Liga se a média de 10 min estiver abaixo de −1800 W e T < `hot_water_surplus_max_temp` (60).
     Desliga se a média de 10 min passar +500 W, ou T ≥ 60.
   - Caso contrário, fica como está se ainda está dentro de um ciclo; senão desliga.
4. **Ciclo mínimo.** Entre duas mudanças automáticas decididas pela automação passam pelo menos 45 min. A hora da
   última mudança fica em `input_datetime.hot_water_last_switched`, escrita pela automação. Não usar o `last_changed`
   do switch: as quedas do Shelly repõem-no. Overrides e mudanças manuais ignoram o ciclo mínimo mas também o atualizam,
   para a automação não inverter logo depois.

Mudança manual no switch (por utilizador, via UI) conta como override: a automação passa o seletor para `Ligada` ou
`Desligada` em vez de a reverter (escolha minha). Mudanças vindas do Shelly (`unavailable`) são ignoradas.

## Overrides

- `input_select.hot_water_override` com `Auto`, `Ligada`, `Desligada`; substitui `input_boolean.force_hot_water_on` e
  `force_hot_water_off` (um seletor evita os dois ligados ao mesmo tempo; escolha minha).
- Uma automação de reposição define `Auto` às 10:00 e às 23:00 (substitui `clear_force_hot_water_helpers.yaml`, que
  corre às 00h, 10h e 20h).
- Os botões ficam no dashboard novo e mostram o estado atual do seletor.

## Dashboard novo

YAML no repo (escolha minha), registado em `configuration.yaml` com chave com hífen, no padrão dos outros.
Conteúdo mínimo: temperatura da água, temperatura prevista no próximo arranque de janela
(`sensor.hot_water_predicted_temperature`, template em `integrations/sensors/`), estado da resistência, botões
`Auto/Ligada/Desligada`, produção e exportação atuais. O desenho visual fica para o plano.

## Ficheiros afetados

Novos: `automations/temperature_and_humidity/control_hot_water.yaml` (substitui o atual), reposição do override,
`integrations/input_select.yaml`, `integrations/sensors/hot_water.yaml`, `dashboards/hot-water.yaml`, entrada em
`configuration.yaml`.

Alterados (precisam de aprovação explícita):
- `integrations/schedule_hot_water.yaml`: passa a conter as janelas de banho (seg-sex 07:00-09:00 e 19:30-21:30; sábado
  09:00-13:00 e 19:30-21:30; domingo 19:30-21:30) em vez das atuais (06:00-08:30 e 17:00-21:30; domingo de manhã
  08:00-10:00).
- `integrations/input_number.yaml`: renomeia `desired_hot_water_temperature` para `desired_hot_water_temperature_winter`
  (a chave `!secret CONST_DESIRED_HOT_WATER_TEMPERATURE` não muda, para não obrigar a mexer no `secrets.yaml` da VM) e
  acrescenta `desired_hot_water_temperature_summer` (50) e `hot_water_surplus_max_temp` (60). Os dois `badge_icon` em
  `home.yaml:181` e `home-office.yaml:236` passam a apontar para o novo id. A entidade antiga fica órfã no registo e
  remove-se depois, com confirmação.
- `integrations/input_datetime.yaml`: acrescenta `hot_water_last_switched`.
- `helpers/input_boolean.yaml`: remove `force_hot_water_on/off`.
- `dashboards/tablet-views/home.yaml` (linhas ~275 e ~293) e `home-office.yaml` (~341 e ~359): os 4 cards de bubble
  que usam os booleanos passam a usar o seletor.
- Apagados: a automação antiga e `automations/others/clear_force_hot_water_helpers.yaml`.

Segue as convenções do repo (um ficheiro por automação, `id` igual ao nome do ficheiro, `alias`, chaves `triggers/
conditions/actions`). Não há `!secret` novos, por isso o `secrets.example.yaml` não muda.

## Validação

- CI: `yamllint` e `check_config` já cobrem a estrutura.
- Antes de ligar: simulação descartável (script no scratchpad, fora do repo) da lógica sobre as duas séries horárias já
  recolhidas (10 dias de Outono e a semana de 22 Jun), para ver horas de arranque e número de mudanças por dia.
- Entrada em produção: a automação nova herda o estado desligado do HA; liga-se à mão na UI depois do merge. Reverter é
  desligar a automação (o switch mantém o último estado).
- Primeiras duas semanas, a observar: temperatura às 07:00 e às 19:30 acima do mínimo em pelo menos 90 % dos dias; no
  máximo 4 mudanças do switch por dia; nenhuma mudança automática com menos de 45 min de intervalo; overrides mantidos
  até à reposição; sem erros da automação no log.

## Fase 2 (fora do âmbito agora)

- Perdas dependentes da temperatura exterior (`sensor.openweathermap_temperature`): perda = k·(T − T exterior), com
  k ~ 0,014; em Junho as perdas a 55-60 ºC foram ~30 % menores que no Outono.
- Previsão solar (`sensor.energy_production_today`/`tomorrow`) para decidir o aquecimento por excedente; ainda não foi
  comparada com a produção real.
- Tarifa horária: hoje a tarifa é simples. Se mudar para bi/tri-horária, o arranque da manhã passa a preferir as
  horas baratas; a discutir quando isso acontecer.

## Por responder

Nada de momento.
