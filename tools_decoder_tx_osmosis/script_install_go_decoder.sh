cd /code/tools_decoder_tx_osmosis;

# get go and install go
rm go1.19.5.linux-amd64.tar.gz;
wget https://go.dev/dl/go1.19.5.linux-amd64.tar.gz;
rm -rf /usr/local/go && tar -C /usr/local -xzf go1.19.5.linux-amd64.tar.gz;
export PATH=$PATH:/usr/local/go/bin;

# compile modified version of osmosis
rm -rf decoder_tx_go_core;
unzip decoder_tx_go_core.zip;
cd decoder_tx_go_core;
make build;
cp ./build/osmosisd /code/osmosisd_decoder;
chmod +x /code/osmosisd_decoder;