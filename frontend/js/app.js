// 聊天应用逻辑
$(document).ready(function() {
    // 服务器地址
    const SERVER_URL = 'http://localhost:9602';
    
    // DOM元素
    // 登录界面元素
    const loginContainer = $('#loginContainer');
    const loginEmail = $('#loginEmail');
    const loginBtn = $('#loginBtn');
    
    // 聊天界面元素
    const chatContainer = $('#chatContainer');
    const currentUser = $('#currentUser');
    const chatMessages = $('#chatMessages');
    const messageInput = $('#message');
    const sendBtn = $('#sendBtn');
    
    // 当前用户信息
    let currentUserEmail = '';
    let isFirstChat = false;
    
    // 登录按钮点击事件
    loginBtn.on('click', function() {
        handleLogin();
    });
    
    // 回车键登录
    loginEmail.on('keypress', function(e) {
        if (e.which === 13) {
            handleLogin();
        }
    });
    
    // 处理登录
    function handleLogin() {
        const email = loginEmail.val().trim();
        
        if (!email) {
            alert('请输入邮箱！');
            return;
        }
        
        currentUserEmail = email;
        
        // 保存邮箱到localStorage
        if (typeof(Storage) !== "undefined") {
            localStorage.setItem('userEmail', email);
        }
        
        // 切换到聊天界面
        loginContainer.hide();
        chatContainer.show();
        currentUser.text(`当前用户: ${email}`);
        
        // 加载聊天记录
        loadChatHistory();
        
        // 检查是否是首次聊天
        checkFirstChat();
    }
    
    // 发送按钮点击事件
    sendBtn.on('click', function() {
        sendMessage();
    });
    
    // 回车键发送消息
    messageInput.on('keypress', function(e) {
        if (e.which === 13) {
            sendMessage();
        }
    });
    
    // 发送消息函数
    function sendMessage() {
        const message = messageInput.val().trim();
        
        if (!message) return;
        
        // 显示用户消息
        addMessage('user', message);
        
        // 保存到聊天记录
        saveChatHistory('user', message);
        
        // 清空输入框
        messageInput.val('');
        
        // 发送请求到服务器
        sendRequest(currentUserEmail, message);
    }
    
    // 发送请求到服务器
    function sendRequest(email, message) {
        // 显示加载状态
        const loadingMessage = addMessage('ai', '<div class="loading"></div>');
        
        // 发送AJAX请求
        $.ajax({
            url: `${SERVER_URL}/chat`,
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                email: email,
                message: message
            }),
            success: function(response) {
                // 移除加载状态
                loadingMessage.remove();
                
                // 显示AI回复
                addMessage('ai', response.response);
                
                // 保存到聊天记录
                saveChatHistory('ai', response.response);
            },
            error: function(xhr, status, error) {
                // 移除加载状态
                loadingMessage.remove();
                
                // 显示错误信息
                const errorMsg = '抱歉，我现在有点忙，稍后再聊吧～';
                addMessage('ai', errorMsg);
                saveChatHistory('ai', errorMsg);
                console.error('请求失败:', error);
            }
        });
    }
    
    // 添加消息到聊天窗口
    function addMessage(type, content) {
        // 创建消息组
        const messageGroup = $('<div>').addClass('message-group');
        
        // 如果是AI消息，处理括号内的神态描述
        if (type === 'ai') {
            // 正则表达式：匹配括号内的神态描述 (内容)
            const expressionRegex = /\(([^)]+)\)/g;
            let match;
            let lastIndex = 0;
            let expressions = [];
            
            // 提取所有神态描述
            while ((match = expressionRegex.exec(content)) !== null) {
                expressions.push({
                    text: match[1],
                    start: match.index,
                    end: match.index + match[0].length
                });
            }
            
            // 如果没有神态描述，直接添加完整消息
            if (expressions.length === 0) {
                const messageDiv = $('<div>').addClass('message').addClass('ai-message');
                messageDiv.html(content);
                messageGroup.append(messageDiv);
            } else {
                // 按顺序添加对话内容和神态描述
                for (let i = 0; i < expressions.length; i++) {
                    const exp = expressions[i];
                    
                    // 添加神态描述前的对话内容
                    if (exp.start > lastIndex) {
                        const textContent = content.substring(lastIndex, exp.start);
                        if (textContent.trim()) {
                            const messageDiv = $('<div>').addClass('message').addClass('ai-message');
                            messageDiv.html(textContent);
                            messageGroup.append(messageDiv);
                        }
                    }
                    
                    // 添加神态描述
                    const expressionDiv = $('<div>').addClass('expression');
                    expressionDiv.text(exp.text);
                    messageGroup.append(expressionDiv);
                    
                    lastIndex = exp.end;
                }
                
                // 添加最后一个神态描述后的对话内容
                if (lastIndex < content.length) {
                    const textContent = content.substring(lastIndex);
                    if (textContent.trim()) {
                        const messageDiv = $('<div>').addClass('message').addClass('ai-message');
                        messageDiv.html(textContent);
                        messageGroup.append(messageDiv);
                    }
                }
            }
        } else {
            // 用户消息直接添加
            const messageDiv = $('<div>').addClass('message').addClass('user-message');
            messageDiv.html(content);
            messageGroup.append(messageDiv);
        }
        
        // 将消息组添加到聊天窗口
        chatMessages.append(messageGroup);
        
        // 滚动到底部
        scrollToBottom();
        
        return messageGroup;
    }
    
    // 滚动到底部
    function scrollToBottom() {
        chatMessages.scrollTop(chatMessages[0].scrollHeight);
    }
    
    // 加载聊天记录
    function loadChatHistory() {
        if (typeof(Storage) !== "undefined") {
            const chatHistoryKey = `chatHistory_${currentUserEmail}`;
            const chatHistory = localStorage.getItem(chatHistoryKey);
            
            if (chatHistory) {
                const messages = JSON.parse(chatHistory);
                messages.forEach(msg => {
                    addMessage(msg.type, msg.content);
                });
            } else {
                isFirstChat = true;
            }
        } else {
            isFirstChat = true;
        }
    }
    
    // 保存聊天记录
    function saveChatHistory(type, content) {
        if (typeof(Storage) !== "undefined") {
            const chatHistoryKey = `chatHistory_${currentUserEmail}`;
            let chatHistory = [];
            
            // 获取现有聊天记录
            const existingHistory = localStorage.getItem(chatHistoryKey);
            if (existingHistory) {
                chatHistory = JSON.parse(existingHistory);
            }
            
            // 添加新消息
            chatHistory.push({
                type: type,
                content: content,
                timestamp: new Date().toISOString()
            });
            
            // 限制聊天记录数量（最多保存100条）
            if (chatHistory.length > 100) {
                chatHistory = chatHistory.slice(-100);
            }
            
            // 保存到localStorage
            localStorage.setItem(chatHistoryKey, JSON.stringify(chatHistory));
        }
    }
    
    // 检查是否是首次聊天
    function checkFirstChat() {
        if (isFirstChat) {
            // 首次聊天，发送隐性提示词获取欢迎语
            sendWelcomePrompt();
        }
    }
    
    // 发送欢迎提示词
    function sendWelcomePrompt() {
        // 显示加载状态
        const loadingMessage = addMessage('ai', '<div class="loading"></div>');
        
        // 隐性提示词，让AI生成欢迎语
        const welcomePrompt = {
            email: currentUserEmail,
            message: "[系统提示：这是用户首次登录，请生成一句友好的欢迎语，介绍自己并询问用户需求]"
        };
        
        // 发送请求到服务器
        $.ajax({
            url: `${SERVER_URL}/chat`,
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(welcomePrompt),
            success: function(response) {
                // 移除加载状态
                loadingMessage.remove();
                
                // 显示AI回复
                addMessage('ai', response.response);
                
                // 保存到聊天记录
                saveChatHistory('ai', response.response);
            },
            error: function(xhr, status, error) {
                // 移除加载状态
                loadingMessage.remove();
                
                // 显示默认欢迎语
                const defaultWelcome = '你好，我是智子，很高兴为你服务！';
                addMessage('ai', defaultWelcome);
                saveChatHistory('ai', defaultWelcome);
                console.error('请求失败:', error);
            }
        });
    }
    
    // 浏览器兼容性检测
    function checkBrowserCompatibility() {
        // 检测是否支持XMLHttpRequest（IE7+支持）
        if (!window.XMLHttpRequest) {
            alert('您的浏览器版本过低，请使用现代浏览器访问！');
        }
        
        // 检测是否支持localStorage
        if (typeof(Storage) !== "undefined") {
            // 自动填充上次登录的邮箱
            const savedEmail = localStorage.getItem('userEmail');
            if (savedEmail) {
                loginEmail.val(savedEmail);
            }
        }
    }
    
    // 初始化浏览器兼容性检测
    checkBrowserCompatibility();
});