# Use CentOS Stream 9 as base image
FROM centos:stream9

ARG KERNEL_VERSION=linux-6.12-rc4.tar.gz


# Copy current directory to /opt/rteval/
COPY . /opt/rteval/

# Install everything in one layer to shrink the image size
# 1: Install needed dependencies and pull kernel source
# 2: install rteval and fix bad symlink
# 3: Remove uneeded packages and shrink the image
RUN dnf -y update && \
    dnf install -y \
        python3-devel \
        python3-lxml \
        python3-libxml2 \
        python3-dmidecode \
        python3-requests \
        realtime-tests \
        sysstat \
        xz \
        bzip2 \
        tar \
        gzip \
        m4 \
        make \
        gawk \
        kernel-headers \
        sos \
        numactl \
        gcc \
        binutils \
        gcc-c++ \
        flex \
        bison \
        bc \
        elfutils \
        elfutils-libelf-devel \
        openssl \
        openssl-devel \
        stress-ng \
        perl-interpreter \
        perl-devel \
        perl-generators \
        libmpc \
        libmpc-devel \
        dwarves \
        wget \
        procps-ng && \
    cd /opt/rteval && \
    wget -P loadsource https://www.kernel.org/pub/linux/kernel/v6.x/${KERNEL_VERSION} && \
    make install && \
    make clean && \
    rm -f /usr/local/bin/rteval && \
    ln -s /opt/rteval/rteval-cmd /usr/bin/rteval && \
    dnf remove -y \
        gcc-c++ \
        python3-devel \
        perl-devel && \
    dnf clean all


# Set the working directory to /root
WORKDIR /root

# Set the entrypoint to a shell
ENTRYPOINT ["/bin/bash"]
