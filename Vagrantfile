Vagrant.configure("2") do |config|
    config.vm.box = "debian/buster64"
    config.vm.network "forwarded_port", guest: 4433, host: 4433, protocol: "udp"
    config.vm.network "forwarded_port", guest: 4433, host: 4433, protocol: "tcp"
end