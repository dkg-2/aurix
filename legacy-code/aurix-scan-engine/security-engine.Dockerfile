# Use a multi-stage or combined build for all security tools
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    wget \
    gnupg \
    tar \
    && rm -rf /var/lib/apt/lists/*

# 1. Install Opengrep (Open-source fork of Semgrep)
# We move the binary to /usr/local/bin so it's globally accessible
RUN curl -fsSL https://raw.githubusercontent.com/opengrep/opengrep/main/install.sh | bash \
    && find /root/.opengrep -name "opengrep" -type f -exec mv {} /usr/local/bin/opengrep \; \
    && chmod +x /usr/local/bin/opengrep

# 2. Install Trivy (Official Repository Method)
RUN wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | gpg --dearmor | tee /usr/share/keyrings/trivy.gpg > /dev/null \
    && echo "deb [signed-by=/usr/share/keyrings/trivy.gpg] https://aquasecurity.github.io/trivy-repo/deb generic main" | tee -a /etc/apt/sources.list.d/trivy.list \
    && apt-get update && apt-get install -y trivy

# 3. Install Gitleaks (Latest v8.30.0)
RUN wget https://github.com/gitleaks/gitleaks/releases/download/v8.30.0/gitleaks_8.30.0_linux_x64.tar.gz \
    && tar -xzf gitleaks_8.30.0_linux_x64.tar.gz \
    && mv gitleaks /usr/local/bin/gitleaks \
    && rm gitleaks_8.30.0_linux_x64.tar.gz

# 4. Install Hadolint (Latest v2.14.0)
RUN wget -O /usr/local/bin/hadolint https://github.com/hadolint/hadolint/releases/download/v2.14.0/hadolint-Linux-x86_64 \
    && chmod +x /usr/local/bin/hadolint

# Set the working directory for scans
WORKDIR /src

# Default command
CMD ["bash"]
