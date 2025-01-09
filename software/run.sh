lxterminal --command 'cd ~/Free*/Code/Server; sudo python main.py; bash'
sleep 2
lxterminal --command 'cd ~/Free*/Code/Client; python Main2.py; bash'
sleep 2
poetry run 01 --server livekit --qr --multimodal
