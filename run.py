# Run Script For The Library Management System Application
#
# This File Serves As The Entry Point For The Flask Application.
# It Imports The Application Factory Function And Creates The App Instance,
# Then Starts The Development Server With Debug Mode Enabled.
#
# For Production Deployment, This File Is Not Used; Instead, A Production
# WSGI Server Like Gunicorn Should Be Used To Serve The Application.

from app import create_app

# Create The Flask Application Instance By Calling The Factory Function.
# The Application Factory Pattern Allows For Better Configuration Management
# And Makes It Easier To Create Multiple App Instances For Testing.
app = create_app()

# Check If This Script Is Being Run Directly (Not Imported As A Module).
# This Prevents The Server From Starting Automatically When The Module Is
# Imported Elsewhere.
if __name__ == '__main__':
    # Start The Flask Development Server.
    #
    # The Debug Mode Provides Several Benefits During Development:
    #   - Automatic Reloading When Code Changes Are Detected.
    #   - Detailed Error Pages With Interactive Debugger.
    #
    # Note: Debug Mode Should Never Be Enabled In Production Environments
    #       As It Poses Security Risks And Performance Overhead.
    app.run(debug=True)