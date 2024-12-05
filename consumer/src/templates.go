package src

var WelcomeHtml = `
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <!-- Header -->
    <div style="text-align: center; margin-bottom: 30px;">
        <img src="https://www.mindkeeperai.com/favicon.svg" alt="Mindkeeper AI" style="width: 60px; height: 60px; margin-bottom: 20px;">
        <h1 style="color: #2563eb; margin: 20px 0;">Your Digital Brain Awaits!</h1>
        <p style="color: #475569; font-size: 18px;">Welcome to MindKeeper AI - the second brain you always needed.</p>
    </div>

    <!-- Welcome Message -->
    <div style="background-color: #f8fafc; padding: 25px; border-radius: 12px; margin-bottom: 30px;">
        <p style="font-size: 16px; color: #1e293b; margin-top: 0;">
            You've just taken the first step towards creating your personal digital brain. Mindkeeper AI transforms how you store, connect, and interact with your knowledge. Let's get you started!
        </p>
    </div>

    <!-- Adding Memories Section -->
    <div style="background-color: #f0f4ff; padding: 25px; border-radius: 12px; border-left: 4px solid #2563eb; margin-bottom: 30px;">
        <div style="display: flex; align-items: start; gap: 15px; margin-bottom: 20px;">
            <div style="background-color: #2563eb; padding: 12px; border-radius: 50%;">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M12 5a3 3 0 1 0-5.997.125 4 4 0 0 0-2.526 5.77 4 4 0 0 0 .556 6.588A4 4 0 1 0 12 18Z"/>
                    <path d="M9 13a4.5 4.5 0 0 0 3-4"/>
                    <path d="M6.003 5.125A3 3 0 0 0 6.401 6.5"/>
                    <path d="M3.477 10.896a4 4 0 0 1 .585-.396"/>
                    <path d="M6 18a4 4 0 0 1-1.967-.516"/>
                    <path d="M12 13h4"/>
                    <path d="M12 18h6a2 2 0 0 1 2 2v1"/>
                    <path d="M12 8h8"/>
                    <path d="M16 8V5a2 2 0 0 1 2-2"/>
                    <circle cx="16" cy="13" r=".5"/>
                    <circle cx="18" cy="3" r=".5"/>
                    <circle cx="20" cy="21" r=".5"/>
                    <circle cx="20" cy="8" r=".5"/>
                </svg>
            </div>
            <h3 style="color: #1e40af; margin: 0; font-size: 20px;">Memory</h3>
        </div>

        <div style="background-color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
            <h4 style="color: #2563eb; margin-top: 0;">You can add following to your digital brain:</h4>
            <ul style="list-style: none; padding: 0; margin: 0;">
                <li style="margin-bottom: 12px; padding-left: 24px; position: relative;">
                    <span style="position: absolute; left: 0; color: #2563eb;">📷</span>
                    <strong>Media Files:</strong> Images, audio, and videos
                </li>
                <li style="margin-bottom: 12px; padding-left: 24px; position: relative;">
                    <span style="position: absolute; left: 0; color: #2563eb;">🎥</span>
                    <strong>YouTube Videos:</strong> Save, learn and analyze videos. Get timestamped citations.
                </li>
                <li style="margin-bottom: 12px; padding-left: 24px; position: relative;">
                    <span style="position: absolute; left: 0; color: #2563eb;">🌐</span>
                    <strong>Web Pages:</strong> Capture any web page
                </li>
                <li style="margin-bottom: 12px; padding-left: 24px; position: relative;">
                    <span style="position: absolute; left: 0; color: #2563eb;">💻</span>
                    <strong>Git Repositories:</strong> Store and analyze code
                </li>
                <li style="margin-bottom: 12px; padding-left: 24px; position: relative;">
                    <span style="position: absolute; left: 0; color: #2563eb;">📝</span>
                    <strong>Notion Pages:</strong> Import your Notion workspace
                </li>
                <li style="padding-left: 24px; position: relative;">
                    <span style="position: absolute; left: 0; color: #2563eb;">📁</span>
                    <strong>Google Drive:</strong> Connect and import documents
                </li>
            </ul>
        </div>

        <div style="text-align: center;">
            <a href="https://www.mindkeeperai.com/" style="display: inline-block; background-color: #2563eb; color: white; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: bold;">
                Start Adding Memories + →
            </a>
        </div>
    </div>

    <!-- Mindmaps Section -->
    <div style="background-color: #f0f4ff; padding: 25px; border-radius: 12px; border-left: 4px solid #7c3aed; margin-bottom: 30px;">
        <div style="display: flex; align-items: start; gap: 15px; margin-bottom: 20px;">
            <div style="background-color: #7c3aed; padding: 12px; border-radius: 50%;">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <rect x="16" y="16" width="6" height="6" rx="1"/>
                    <rect x="2" y="16" width="6" height="6" rx="1"/>
                    <rect x="9" y="2" width="6" height="6" rx="1"/>
                    <path d="M5 16v-3a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1v3"/>
                    <path d="M12 12V8"/>
                </svg>
            </div>
            <h3 style="color: #5b21b6; margin: 0; font-size: 20px;">Connect & Discover</h3>
        </div>

        <div style="background-color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
            <h4 style="color: #7c3aed; margin-top: 0;">Create Powerful Mindmaps</h4>
            <p style="color: #475569;">Transform scattered memories into connected knowledge:</p>
            <ul style="color: #475569; padding-left: 20px;">
                <li style="margin-bottom: 8px;">Combine related memories into interactive mindmaps</li>
                <li style="margin-bottom: 8px;">Discover hidden connections in your knowledge</li>
                <li style="margin-bottom: 8px;">Chat with multiple connected memories at once</li>
                <li>Generate cross-memory insights and summaries</li>
            </ul>
        </div>

        <div style="text-align: center;">
            <a href="https://www.mindkeeperai.com/mindmaps" style="display: inline-block; background-color: #7c3aed; color: white; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: bold;">
                Explore Mindmaps →
            </a>
        </div>
    </div>

    <!-- Chat Section -->
    <div style="background-color: #f0f4ff; padding: 25px; border-radius: 12px; border-left: 4px solid #2563eb; margin-bottom: 30px;">
        <h3 style="color: #1e40af; margin-top: 0;">Meet Your Digital Twin</h3>

        <div style="display: flex; align-items: start; gap: 15px; margin-bottom: 20px;">
            <div style="background-color: #2563eb; padding: 12px; border-radius: 50%;">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M12 5a3 3 0 1 0-5.997.125 4 4 0 0 0-2.526 5.77 4 4 0 0 0 .556 6.588A4 4 0 1 0 12 18Z"/>
                    <path d="M9 13a4.5 4.5 0 0 0 3-4"/>
                    <path d="M12 13h4"/>
                    <path d="M12 18h6a2 2 0 0 1 2 2v1"/>
                    <path d="M12 8h8"/>
                    <path d="M16 8V5a2 2 0 0 1 2-2"/>
                </svg>
            </div>
            <p style="margin: 0; color: #1e40af; font-size: 16px; flex: 1;">
                Imagine having a conversation with a version of yourself that remembers <em>everything</em> you've ever learned, read, or saved. That's what chatting with Mindkeeper feels like.
            </p>
        </div>

        <div style="background-color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
            <h4 style="color: #2563eb; margin-top: 0;">Three Powerful Ways to Chat:</h4>

            <div style="margin-bottom: 15px;">
                <p style="font-weight: bold; color: #1e40af; margin-bottom: 5px;">🧠 Memory mode</p>
                <p style="color: #475569; margin: 0;">Retrieves information specifically based on contents you added as memories with accurate citations.</p>
            </div>

            <div style="margin-bottom: 15px;">
                <p style="font-weight: bold; color: #1e40af; margin-bottom: 5px;">🌐 Web-Enhanced Mode</p>
                <p style="color: #475569; margin: 0;">Enable web search to combine your personal knowledge with the latest information from the internet. Get responses that blend your perspective with current facts and developments.</p>
            </div>

            <div style="margin-bottom: 15px;">
                <p style="font-weight: bold; color: #1e40af; margin-bottom: 5px;">🔄 Hybrid Intelligence</p>
                <p style="color: #475569; margin: 0;">Use both modes together for the ultimate experience - your personal knowledge enriched with web intelligence. Perfect for research, decision-making, and generating comprehensive insights.</p>
            </div>
        </div>

        <div style="text-align: center;">
            <p style="color: #475569; font-style: italic; margin-bottom: 20px;">
                "It's like having a conversation with a version of yourself that never forgets!"
            </p>
            <a href="https://www.mindkeeperai.com/" style="display: inline-block; background-color: #2563eb; color: white; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: bold;">
                Start Chatting with Your Digital Twin →
            </a>
        </div>
    </div>

    <!-- Quick Start Guide -->
    <div style="background-color: #f8fafc; padding: 25px; border-radius: 12px; margin-bottom: 30px;">
        <h3 style="color: #1e40af; margin-top: 0;">Quick Start Guide</h3>
        <ol style="color: #475569; padding-left: 20px;">
            <li style="margin-bottom: 15px;">
                <strong>Add Your First Memory</strong><br>
                Click the '+' icon and upload any type of content
            </li>
            <li style="margin-bottom: 15px;">
                <strong>Create a Mindmap</strong><br>
                Connect two or more related memories
            </li>
            <li style="margin-bottom: 15px;">
                <strong>Start a Conversation</strong><br>
                Chat with your digital brain and explore your knowledge
            </li>
        </ol>
    </div>
    </body>
    </html>
`
