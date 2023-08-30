# Websocket TCP Encapsulator
This simple script allows you to remotely access devices on another network where you can't open ports on the router.
I'm using this code in a personal project, and I'd like to share it with you. ^^

**Explain in image :**
![image](https://github.com/EliotAmn/websocket-tcp-encapsulator/assets/73363100/1bbfaf31-bed2-46c2-91cd-84651ad52035)

**Config corresponding to the image :**
```
config = {
    "servers": [
        {
            "name": "my-client",
            "listen_port": 3033,
            "password": "MySecretPassword",
            "ports": {
                "4000": {
                    "redirect_ip": "192.168.1.12",
                    "redirect_port": 80
                }
            }
        }
    ]
}

```
