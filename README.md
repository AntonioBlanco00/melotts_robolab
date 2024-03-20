# melotts_robolab
Componente que recibe una string y la reproduce TTS.
Necesita estar conectado a internet por cable, y a EBO por wifi.


## Configuration parameters
As any other component, *melotts_robolab* needs a configuration file to start. In
```
etc/config
```
you can find an example of a configuration file. We can find there the following lines:
```
# Endpoints for implements interfaces
Speech.Endpoints=tcp -p 11339


# Proxies for required interfaces
EmotionalMotorProxy = emotionalmotor:tcp -h 192.168.16.1 -p 30001

# 192.168.16.1 es la ip para conectarse a EBO


Ice.Warn.Connections=0
Ice.Trace.Network=0
Ice.Trace.Protocol=0
Ice.MessageSizeMax=20004800

```

## Starting the component
To avoid changing the *config* file in the repository, we can copy it to the component's home directory, so changes will remain untouched by future git pulls:

```
cd <melotts_robolab's path> 
```
```
cp etc/config config
```

After editing the new config file we can run the component:

```
bin/melotts_robolab config
```
