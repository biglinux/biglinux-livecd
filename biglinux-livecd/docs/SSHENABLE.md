# `sshenable` no live do BigLinux

Adicionar `sshenable` à linha de comando do kernel ativa o servidor SSH do
live, útil quando a máquina não aceita interação local durante uma falha de
boot.

O serviço usa o usuário local de UID `1000`, que é o usuário padrão do live.
O nome é lido de `/etc/passwd`, portanto pode ser `biglinux` ou outro nome
fornecido por uma personalização. A senha temporária definida para esse
usuário é `big`. Nenhuma conta é criada e as senhas, grupos e permissões dos
demais usuários não são alterados.

De outro computador na mesma rede:

```text
ssh <usuario-do-live>@<ip-do-live>
```

Informe a senha `big`. O endereço pode ser obtido no live com `ip address` ou
no roteador. O SSH não deve ser exposto à Internet: a senha é conhecida e o
recurso existe para recuperação local. O usuário root não pode acessar por
senha (`PermitRootLogin no`).

Para desativar o recurso, reinicie o live sem `sshenable`; a alteração é
efêmera e não é gravada no sistema instalado.
