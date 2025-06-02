package com;

import com.google.gson.*;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.*;
import java.util.stream.*;

public class MinecraftLauncherCore {

    private static final int TCP_PORT = 25589;
    private static final String AUTH_URL = "https://authserver.mojang.com/authenticate";
    private static final ExecutorService executor = Executors.newCachedThreadPool();
    private static Process minecraftProcess;
    private static final ScheduledExecutorService scheduler = Executors.newScheduledThreadPool(1);
    private static final Map<String, String> customArgs = new ConcurrentHashMap<>();
    private static final String GAME_DIR_FILE = "game_dirs.cache";
    private static final Map<String, String> gameDirCache = new ConcurrentHashMap<>();
    private static String defaultMinecraftDir; // 存储默认的.minecraft目录

    public static void main(String[] args) {
        System.out.println("Minecraft启动器核心 v1.1");
        System.out.println("正在初始化...");

        loadCustomArgs();
        loadGameDirsCache();

        // 尝试自动查找默认的.minecraft目录
        defaultMinecraftDir = findDefaultMinecraftDir();
        if (defaultMinecraftDir != null) {
            System.out.println("找到默认Minecraft目录: " + defaultMinecraftDir);
        } else {
            System.out.println("警告: 未找到默认Minecraft目录");
        }

        startTCPServer();
        startMemoryCleaner();
        addShutdownHook();

        System.out.println("系统已就绪，等待指令");
        printMemoryUsage();
    }

    // 查找默认的.minecraft目录
    private static String findDefaultMinecraftDir() {
        // 尝试从缓存中获取
        String cachedDir = gameDirCache.get(".minecraft");
        if (cachedDir != null && new File(cachedDir).exists()) {
            return cachedDir;
        }

        // 根据操作系统查找标准位置
        String os = System.getProperty("os.name").toLowerCase();
        String home = System.getProperty("user.home");
        String path = null;

        if (os.contains("win")) {
            path = home + File.separator + "AppData" + File.separator + "Roaming" + File.separator + ".minecraft";
        } else if (os.contains("mac")) {
            path = home + File.separator + "Library" + File.separator + "Application Support" + File.separator + "minecraft";
        } else { // Linux/Unix
            path = home + File.separator + ".minecraft";
        }

        if (new File(path).exists()) {
            gameDirCache.put(".minecraft", path);
            return path;
        }

        // 尝试用户目录下的常见位置
        File userDir = new File(home);
        File[] possibleDirs = userDir.listFiles((dir, name) ->
                name.equalsIgnoreCase(".minecraft") ||
                        name.equalsIgnoreCase("minecraft"));

        if (possibleDirs != null) {
            for (File dir : possibleDirs) {
                if (dir.isDirectory()) {
                    gameDirCache.put(".minecraft", dir.getAbsolutePath());
                    return dir.getAbsolutePath();
                }
            }
        }

        return null;
    }

    private static void startTCPServer() {
        executor.submit(() -> {
            try (ServerSocket serverSocket = new ServerSocket(TCP_PORT)) {
                System.out.println("启动器核心已启动，监听端口: " + TCP_PORT);

                while (!Thread.currentThread().isInterrupted()) {
                    try (Socket clientSocket = serverSocket.accept();
                         BufferedReader in = new BufferedReader(new InputStreamReader(clientSocket.getInputStream()));
                         PrintWriter out = new PrintWriter(clientSocket.getOutputStream(), true)) {

                        String message = in.readLine();
                        System.out.println("收到消息: " + message);

                        JsonObject response;
                        if (message.startsWith("LAUNCH:")) {
                            response = handleLaunchRequest(message.substring(7));
                        } else if (message.startsWith("SET_CUSTOM_ARG:")) {
                            response = handleSetCustomArg(message.substring(15));
                        } else if (message.startsWith("FIND_GAME_DIR:")) {
                            response = handleFindGameDir(message.substring(13));
                        } else if (message.startsWith("SET_MINECRAFT_DIR:")) {
                            response = handleSetMinecraftDir(message.substring(18));
                        } else if (message.equals("GET_STATUS")) {
                            response = handleStatusRequest();
                        } else if (message.equals("GET_VERSIONS")) {
                            response = handleGetVersions();
                        } else {
                            response = new JsonObject();
                            response.addProperty("status", "error");
                            response.addProperty("message", "未知命令");
                        }

                        out.println(response.toString());
                    } catch (Exception e) {
                        System.err.println("客户端通信错误: " + e.getMessage());
                    }
                }
            } catch (IOException e) {
                System.err.println("服务器启动失败: " + e.getMessage());
                System.exit(1);
            }
        });
    }

    // 处理获取版本列表请求
    private static JsonObject handleGetVersions() {
        JsonObject response = new JsonObject();
        try {
            String mcDir = defaultMinecraftDir;
            if (mcDir == null) {
                response.addProperty("status", "error");
                response.addProperty("message", "未设置Minecraft目录");
                return response;
            }

            File versionsDir = new File(mcDir, "versions");
            if (!versionsDir.exists() || !versionsDir.isDirectory()) {
                response.addProperty("status", "error");
                response.addProperty("message", "versions目录不存在");
                return response;
            }

            File[] versionDirs = versionsDir.listFiles(File::isDirectory);
            if (versionDirs == null || versionDirs.length == 0) {
                response.addProperty("status", "error");
                response.addProperty("message", "未找到游戏版本");
                return response;
            }

            JsonArray versions = new JsonArray();
            for (File dir : versionDirs) {
                // 检查版本目录是否有效（包含必要的文件）
                if (isValidVersionDir(dir)) {
                    versions.add(dir.getName());
                }
            }

            if (versions.size() == 0) {
                response.addProperty("status", "error");
                response.addProperty("message", "未找到有效的游戏版本");
                return response;
            }

            response.addProperty("status", "success");
            response.add("versions", versions);
            return response;
        } catch (Exception e) {
            response.addProperty("status", "error");
            response.addProperty("message", "获取版本错误: " + e.getMessage());
            return response;
        }
    }

    // 验证版本目录是否有效
    private static boolean isValidVersionDir(File versionDir) {
        // 检查是否存在必要的文件
        File jarFile = new File(versionDir, versionDir.getName() + ".jar");
        File jsonFile = new File(versionDir, versionDir.getName() + ".json");

        return jarFile.exists() && jsonFile.exists();
    }

    // 处理设置Minecraft目录请求
    private static JsonObject handleSetMinecraftDir(String path) {
        JsonObject response = new JsonObject();
        try {
            File dir = new File(path);
            if (!dir.exists() || !dir.isDirectory()) {
                response.addProperty("status", "error");
                response.addProperty("message", "目录不存在");
                return response;
            }

            // 验证是否为有效的.minecraft目录
            File versionsDir = new File(dir, "versions");
            if (!versionsDir.exists() || !versionsDir.isDirectory()) {
                response.addProperty("status", "error");
                response.addProperty("message", "无效的Minecraft目录");
                return response;
            }

            defaultMinecraftDir = path;
            gameDirCache.put(".minecraft", path);
            saveGameDirsCache();

            response.addProperty("status", "success");
            response.addProperty("message", "Minecraft目录设置成功");
            return response;
        } catch (Exception e) {
            response.addProperty("status", "error");
            response.addProperty("message", "设置错误: " + e.getMessage());
            return response;
        }
    }

    private static JsonObject handleLaunchRequest(String json) {
        JsonObject response = new JsonObject();
        try {
            JsonObject config = JsonParser.parseString(json).getAsJsonObject();

            // 获取游戏目录 - 优先使用配置中的目录
            String gameDir = resolveGameDir(config);

            // 如果未指定目录，使用默认的.minecraft目录
            if (gameDir == null) {
                if (defaultMinecraftDir != null) {
                    gameDir = defaultMinecraftDir;
                    System.out.println("使用默认Minecraft目录: " + gameDir);
                } else {
                    response.addProperty("status", "error");
                    response.addProperty("message", "未指定游戏目录且无默认目录");
                    return response;
                }
            }

            // 检查版本是否存在
            String version = config.get("version").getAsString();
            File versionDir = new File(gameDir, "versions" + File.separator + version);
            if (!versionDir.exists() || !isValidVersionDir(versionDir)) {
                response.addProperty("status", "error");
                response.addProperty("message", "无效的游戏版本: " + version);
                return response;
            }

            // 处理认证
            AuthResult auth = null;
            boolean onlineMode = config.has("onlineMode") && config.get("onlineMode").getAsBoolean();

            if (onlineMode) {
                System.out.println("使用正版认证模式");
                auth = authenticate(
                        config.get("username").getAsString(),
                        config.get("password").getAsString()
                );
            } else {
                System.out.println("使用离线模式");
                String username = config.get("username").getAsString();
                auth = offlineAuthenticate(username);
            }

            // 启动游戏
            if (auth != null) {
                startMinecraft(config, auth, gameDir);
                response.addProperty("status", "success");
                response.addProperty("message", "游戏启动中");
                response.addProperty("playerName", auth.playerName);
            } else {
                response.addProperty("status", "error");
                response.addProperty("message", "认证失败");
            }
        } catch (Exception e) {
            response.addProperty("status", "error");
            response.addProperty("message", "启动错误: " + e.getMessage());
            e.printStackTrace();
        }
        return response;
    }

    // 其他方法保持不变（handleSetCustomArg, handleFindGameDir, handleStatusRequest等）
    // 为了简洁，这里省略了未修改的方法，实际代码中需要保留

    private static JsonObject handleSetCustomArg(String argStr) {
        JsonObject response = new JsonObject();
        try {
            String[] parts = argStr.split("=", 2);
            if (parts.length == 2) {
                customArgs.put(parts[0], parts[1]);
                saveCustomArgs();
                response.addProperty("status", "success");
                response.addProperty("message", "参数设置成功");
            } else {
                response.addProperty("status", "error");
                response.addProperty("message", "参数格式错误");
            }
        } catch (Exception e) {
            response.addProperty("status", "error");
            response.addProperty("message", "设置错误: " + e.getMessage());
        }
        return response;
    }

    private static JsonObject handleFindGameDir(String gameName) {
        JsonObject response = new JsonObject();
        try {
            String gameDir = findGameDirectory(gameName);
            if (gameDir != null) {
                response.addProperty("status", "success");
                response.addProperty("path", gameDir);
                cacheGameDir(gameName, gameDir);
            } else {
                response.addProperty("status", "error");
                response.addProperty("message", "未找到游戏目录");
            }
        } catch (Exception e) {
            response.addProperty("status", "error");
            response.addProperty("message", "查找错误: " + e.getMessage());
        }
        return response;
    }

    private static JsonObject handleStatusRequest() {
        JsonObject response = new JsonObject();
        response.addProperty("status", "success");
        response.addProperty("running", minecraftProcess != null && minecraftProcess.isAlive());
        response.addProperty("customArgsCount", customArgs.size());
        response.addProperty("cachedDirsCount", gameDirCache.size());
        response.addProperty("minecraftDir", defaultMinecraftDir != null ? defaultMinecraftDir : "未设置");

        Runtime runtime = Runtime.getRuntime();
        long used = runtime.totalMemory() - runtime.freeMemory();
        long max = runtime.maxMemory();
        response.addProperty("memoryUsed", used);
        response.addProperty("memoryMax", max);

        return response;
    }

    private static String resolveGameDir(JsonObject config) {
        if (config.has("gameDir")) {
            return config.get("gameDir").getAsString();
        }
        if (config.has("gameName")) {
            return findGameDirectory(config.get("gameName").getAsString());
        }
        return null;
    }

    private static String findGameDirectory(String gameName) {
        // 从缓存中查找
        String cachedDir = gameDirCache.get(gameName);
        if (cachedDir != null && new File(cachedDir).exists()) {
            return cachedDir;
        }

        // 常见Minecraft目录位置
        String os = System.getProperty("os.name").toLowerCase();
        String home = System.getProperty("user.home");

        List<String> searchPaths = new ArrayList<>();

        if (os.contains("win")) {
            searchPaths.add(home + File.separator + "AppData" + File.separator + "Roaming" + File.separator + "." + gameName);
            searchPaths.add("C:\\" + gameName);
            searchPaths.add("D:\\" + gameName);
        } else if (os.contains("mac")) {
            searchPaths.add(home + File.separator + "Library" + File.separator + "Application Support" + File.separator + gameName);
        } else { // Linux/Unix
            searchPaths.add(home + File.separator + "." + gameName);
        }

        // 通用位置
        searchPaths.add(home + File.separator + gameName);
        searchPaths.add(home + File.separator + gameName + "_data");
        searchPaths.add("/opt/" + gameName);

        for (String path : searchPaths) {
            File dir = new File(path);
            if (dir.exists() && dir.isDirectory()) {
                gameDirCache.put(gameName, path);
                return path;
            }
        }

        // 尝试在用户目录下搜索
        File userDir = new File(home);
        File[] possibleDirs = userDir.listFiles((dir, name) ->
                name.equalsIgnoreCase(gameName) ||
                        name.equalsIgnoreCase("." + gameName) ||
                        name.equalsIgnoreCase(gameName + "_data"));

        if (possibleDirs != null && possibleDirs.length > 0) {
            for (File dir : possibleDirs) {
                if (dir.isDirectory()) {
                    gameDirCache.put(gameName, dir.getAbsolutePath());
                    return dir.getAbsolutePath();
                }
            }
        }

        return null;
    }

    private static AuthResult authenticate(String username, String password) {
        try {
            System.out.println("正在认证: " + username);
            HttpURLConnection conn = (HttpURLConnection) new URL(AUTH_URL).openConnection();
            conn.setRequestMethod("POST");
            conn.setRequestProperty("Content-Type", "application/json");
            conn.setDoOutput(true);
            conn.setConnectTimeout(10000);
            conn.setReadTimeout(10000);

            JsonObject authData = new JsonObject();
            authData.addProperty("agent", "Minecraft");
            authData.addProperty("username", username);
            authData.addProperty("password", password);
            authData.addProperty("clientToken", UUID.randomUUID().toString());

            try (OutputStream os = conn.getOutputStream()) {
                os.write(authData.toString().getBytes(StandardCharsets.UTF_8));
                os.flush();
            }

            if (conn.getResponseCode() == 200) {
                try (BufferedReader br = new BufferedReader(new InputStreamReader(conn.getInputStream()))) {
                    JsonObject response = JsonParser.parseReader(br).getAsJsonObject();
                    JsonObject profile = response.getAsJsonObject("selectedProfile");
                    return new AuthResult(
                            response.get("accessToken").getAsString(),
                            profile.get("id").getAsString(),
                            profile.get("name").getAsString()
                    );
                }
            } else {
                try (BufferedReader br = new BufferedReader(new InputStreamReader(conn.getErrorStream()))) {
                    String errorResponse = br.lines().collect(Collectors.joining());
                    System.err.println("认证失败: HTTP " + conn.getResponseCode() + " - " + errorResponse);
                }
            }
        } catch (Exception e) {
            System.err.println("认证错误: " + e.getMessage());
        }
        return null;
    }

    private static AuthResult offlineAuthenticate(String username) {
        // 生成离线UUID（基于用户名）
        UUID uuid = UUID.nameUUIDFromBytes(("OfflinePlayer:" + username).getBytes(StandardCharsets.UTF_8));
        return new AuthResult(
                "offline_access_token",
                uuid.toString().replace("-", ""),
                username
        );
    }

    private static void startMinecraft(JsonObject config, AuthResult auth, String gameDir) throws Exception {
        // 如果已有游戏运行则终止
        if (minecraftProcess != null && minecraftProcess.isAlive()) {
            System.out.println("终止正在运行的游戏进程...");
            minecraftProcess.destroy();
            minecraftProcess.waitFor(5, TimeUnit.SECONDS);
        }

        System.out.println("启动游戏: " + config.get("version").getAsString());
        System.out.println("玩家: " + auth.playerName);
        System.out.println("游戏目录: " + gameDir);

        // 构建JVM参数
        List<String> command = new ArrayList<>();
        command.add(config.get("javaPath").getAsString());

        // 添加内存设置
        int minMemory = config.has("minMemory") ? config.get("minMemory").getAsInt() : 1024;
        int maxMemory = config.get("maxMemory").getAsInt();
        command.add("-Xms" + minMemory + "M");
        command.add("-Xmx" + maxMemory + "M");

        // 添加自定义JVM参数
        for (String arg : customArgs.keySet()) {
            if (arg.startsWith("jvm.")) {
                command.add(customArgs.get(arg));
            }
        }

        // 添加标准JVM参数
        if (config.has("jvmArgs")) {
            JsonArray jvmArgs = config.getAsJsonArray("jvmArgs");
            for (JsonElement arg : jvmArgs) {
                command.add(arg.getAsString());
            }
        }

        // 添加主类
        command.add(config.get("mainClass").getAsString());

        // 添加游戏参数
        command.add("--username");
        command.add(auth.playerName);
        command.add("--uuid");
        command.add(auth.uuid);
        command.add("--accessToken");
        command.add(auth.accessToken);
        command.add("--version");
        command.add(config.get("version").getAsString());
        command.add("--gameDir");
        command.add(gameDir);
        command.add("--assetsDir");
        command.add(gameDir + File.separator + "assets");

        // 添加自定义游戏参数
        for (String arg : customArgs.keySet()) {
            if (arg.startsWith("game.")) {
                command.add("--" + arg.substring(5));
                command.add(customArgs.get(arg));
            }
        }

        // 添加标准游戏参数
        if (config.has("gameArgs")) {
            JsonObject gameArgs = config.getAsJsonObject("gameArgs");
            for (String key : gameArgs.keySet()) {
                command.add("--" + key);
                command.add(gameArgs.get(key).getAsString());
            }
        }

        // 打印启动命令（调试用）
        System.out.println("启动命令: " + String.join(" ", command));

        // 启动进程
        ProcessBuilder pb = new ProcessBuilder(command);
        pb.directory(new File(gameDir));
        pb.redirectErrorStream(true);

        minecraftProcess = pb.start();

        // 处理游戏输出 - 实时打印到控制台
        executor.submit(() -> {
            try (BufferedReader reader = new BufferedReader(
                    new InputStreamReader(minecraftProcess.getInputStream()))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    System.out.println("[MC] " + line);
                }
                int exitCode = minecraftProcess.waitFor();
                System.out.println("游戏进程退出，代码: " + exitCode);
            } catch (Exception e) {
                System.err.println("游戏输出读取错误: " + e.getMessage());
            }
        });
    }

    private static void startMemoryCleaner() {
        scheduler.scheduleAtFixedRate(() -> {
            System.out.println("执行内存清理...");
            System.gc();
            System.runFinalization();
            printMemoryUsage();
        }, 30, 30, TimeUnit.MINUTES);
    }

    private static void printMemoryUsage() {
        Runtime runtime = Runtime.getRuntime();
        long used = runtime.totalMemory() - runtime.freeMemory();
        long max = runtime.maxMemory();
        System.out.printf("内存使用: %.2fMB/%.2fMB (%.1f%%)%n",
                used / (1024.0 * 1024.0),
                max / (1024.0 * 1024.0),
                (used * 100.0) / max);
    }

    private static void addShutdownHook() {
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            System.out.println("关闭启动器...");
            if (minecraftProcess != null && minecraftProcess.isAlive()) {
                System.out.println("终止游戏进程...");
                minecraftProcess.destroy();
                try {
                    minecraftProcess.waitFor(3, TimeUnit.SECONDS);
                } catch (InterruptedException e) {
                    System.err.println("等待进程关闭时出错: " + e.getMessage());
                }
            }

            System.out.println("关闭调度器...");
            scheduler.shutdown();
            try {
                if (!scheduler.awaitTermination(5, TimeUnit.SECONDS)) {
                    scheduler.shutdownNow();
                }
            } catch (InterruptedException e) {
                scheduler.shutdownNow();
            }

            System.out.println("关闭线程池...");
            executor.shutdown();
            try {
                if (!executor.awaitTermination(5, TimeUnit.SECONDS)) {
                    executor.shutdownNow();
                }
            } catch (InterruptedException e) {
                executor.shutdownNow();
            }

            saveCustomArgs();
            saveGameDirsCache();
            System.out.println("启动器已关闭");
        }));
    }

    // 自定义参数持久化
    private static void saveCustomArgs() {
        try (PrintWriter out = new PrintWriter("custom_args.cfg")) {
            for (Map.Entry<String, String> entry : customArgs.entrySet()) {
                out.println(entry.getKey() + "=" + entry.getValue());
            }
            System.out.println("保存自定义参数: " + customArgs.size() + " 条");
        } catch (IOException e) {
            System.err.println("保存自定义参数失败: " + e.getMessage());
        }
    }

    private static void loadCustomArgs() {
        File file = new File("custom_args.cfg");
        if (file.exists()) {
            try (BufferedReader reader = new BufferedReader(new FileReader(file))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    String[] parts = line.split("=", 2);
                    if (parts.length == 2) {
                        customArgs.put(parts[0], parts[1]);
                    }
                }
                System.out.println("已加载自定义参数: " + customArgs.size() + " 条");
            } catch (IOException e) {
                System.err.println("加载自定义参数失败: " + e.getMessage());
            }
        }
    }

    // 游戏目录缓存
    private static void cacheGameDir(String gameName, String path) {
        gameDirCache.put(gameName, path);
    }

    private static void saveGameDirsCache() {
        try (PrintWriter out = new PrintWriter(new FileWriter(GAME_DIR_FILE))) {
            for (Map.Entry<String, String> entry : gameDirCache.entrySet()) {
                out.println(entry.getKey() + "=" + entry.getValue());
            }
            System.out.println("保存游戏目录缓存: " + gameDirCache.size() + " 条");
        } catch (IOException e) {
            System.err.println("保存游戏目录缓存失败: " + e.getMessage());
        }
    }

    private static void loadGameDirsCache() {
        File file = new File(GAME_DIR_FILE);
        if (file.exists()) {
            try (BufferedReader reader = new BufferedReader(new FileReader(file))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    String[] parts = line.split("=", 2);
                    if (parts.length == 2) {
                        gameDirCache.put(parts[0], parts[1]);
                    }
                }
                System.out.println("已加载游戏目录缓存: " + gameDirCache.size() + " 条");
            } catch (IOException e) {
                System.err.println("加载游戏目录缓存失败: " + e.getMessage());
            }
        }
    }

    static class AuthResult {
        final String accessToken;
        final String uuid;
        final String playerName;

        AuthResult(String accessToken, String uuid, String playerName) {
            this.accessToken = accessToken;
            this.uuid = uuid;
            this.playerName = playerName;
        }
    }
}