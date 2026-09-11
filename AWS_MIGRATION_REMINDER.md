# AURIX Project - AWS Migration & Updates Guide

This document was created after the repository was reorganized into a standard Mono-Repo structure. **Because folder names changed, your AWS server will break the next time you `git pull`.** 

Here is exactly what you need to do to fix it:

## 1. Stop the old Daemon
SSH into your AWS EC2 instance:
```bash
ssh -i aurix-key.pem ubuntu@65.0.134.65
```
Find the old `queue_listener.py` background process and kill it:
```bash
ps aux | grep queue_listener
kill -9 <PID>
```

## 2. Pull the New Code
```bash
cd ~/aurix
git pull origin main
```

## 3. Update the `.env` Paths
Because `new work` was renamed to `ai-engine-core`, you must update the absolute paths in your `.env` file!
```bash
nano ~/aurix/ai-engine-core/.env
```
Change the `WORKSPACE_MOUNT_PATH` from:
`/home/ubuntu/aurix/new work/workspace`
**To:**
`/home/ubuntu/aurix/ai-engine-core/workspace`

## 4. Restart the Daemon
Now start the listener from the new folder:
```bash
cd ~/aurix/ai-engine-core
nohup python3 -u queue_listener.py > queue_listener.log 2>&1 &
```

That's it! Your AWS server will now be perfectly synced with the new folder structure.
