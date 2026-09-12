#!/bin/csh
# Create FIFO pipe if it doesn't exist
if ( ! -e MCP.command ) then
    mkfifo MCP.command
    echo "Created FIFO pipe: MCP.command"
else
    echo "FIFO pipe MCP.command already exists."
endif

# Source Cadence CMOS 65nm environment setup script
if ( -e .cshrc_cmos065 ) then
    source .cshrc_cmos065
endif

# Suppress Cadence license queue popups, architecture prompts, and agreements
setenv CDS_LIC_QUEUE_TIMEOUT 0
setenv CDS_LIC_QA_Action 1
setenv CDS_AUTO_64BIT ALL

# Set DISPLAY if not already set (default to :0 for local display/VNC)
if ( ! $?DISPLAY ) then
    setenv DISPLAY :0
endif

virtuoso -nosplash >& virtuoso_launch.log &
