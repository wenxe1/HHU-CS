import java.sql.*;

public class TestConn {
    public static void main(String[] args) {
        // 替换为你的公网 IP
        String url = "jdbc:postgresql://120.46.20.99:26000/campus_card?ApplicationName=app1";
        String user = "card_user";
        String pass = "Gauss#3campus";

        try {
            Class.forName("org.postgresql.Driver");
            System.out.println("驱动加载成功，正在连接...");

            // 尝试连接（设置5秒超时）
            DriverManager.setLoginTimeout(5);
            Connection conn = DriverManager.getConnection(url, user, pass);

            System.out.println("✅ 恭喜！数据库连接成功！");
            conn.close();
        } catch (Exception e) {
            System.err.println("❌ 连接失败，原因如下：");
            e.printStackTrace();
        }
    }
}