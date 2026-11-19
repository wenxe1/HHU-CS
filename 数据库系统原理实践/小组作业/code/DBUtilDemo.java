import java.sql.*;
import java.util.Vector;

public class DBUtilDemo {
    // --- 数据库连接配置 ---
    static final String JDBC_DRIVER = "org.postgresql.Driver";
    static final String DB_URL = "jdbc:postgresql://120.46.20.99:26000/campus_card?ApplicationName=app1";
    static final String USER = "admin";
    static final String PASS = "Admin@123";

    static {
        try {
            Class.forName(JDBC_DRIVER);
        } catch (ClassNotFoundException e) {
            e.printStackTrace();
            System.err.println("错误：未找到 JDBC 驱动！请检查 postgresql.jar 是否在 classpath 中");
        }
    }

    public static Connection getConnection() throws SQLException {
        DriverManager.setLoginTimeout(5); // 设置连接超时
        return DriverManager.getConnection(DB_URL, USER, PASS);
    }

    /**
     * 执行查询 (SELECT)
     */
    public static QueryResult executeQuery(String sql) {
        Vector<String> columnNames = new Vector<>();
        Vector<Vector<Object>> data = new Vector<>();
        String errorMsg = null;

        try (Connection conn = getConnection();
             Statement stmt = conn.createStatement();
             ResultSet rs = stmt.executeQuery(sql)) {

            ResultSetMetaData metaData = rs.getMetaData();
            int columnCount = metaData.getColumnCount();
            for (int i = 1; i <= columnCount; i++) {
                columnNames.add(metaData.getColumnName(i));
            }

            while (rs.next()) {
                Vector<Object> row = new Vector<>();
                for (int i = 1; i <= columnCount; i++) {
                    row.add(rs.getObject(i));
                }
                data.add(row);
            }

        } catch (SQLException e) {
            errorMsg = "SQL错误: " + e.getMessage();
            e.printStackTrace();
        }

        return new QueryResult(columnNames, data, errorMsg);
    }

    public static QueryResult executeQueryParams(String sql, Object... params) {
        Vector<String> columnNames = new Vector<>();
        Vector<Vector<Object>> data = new Vector<>();
        String errorMsg = null;
        try (Connection conn = getConnection();
             PreparedStatement ps = conn.prepareStatement(sql)) {
            for (int i = 0; i < params.length; i++) {
                ps.setObject(i + 1, params[i]);
            }
            try (ResultSet rs = ps.executeQuery()) {
                ResultSetMetaData metaData = rs.getMetaData();
                int columnCount = metaData.getColumnCount();
                for (int i = 1; i <= columnCount; i++) {
                    columnNames.add(metaData.getColumnName(i));
                }
                while (rs.next()) {
                    Vector<Object> row = new Vector<>();
                    for (int i = 1; i <= columnCount; i++) {
                        row.add(rs.getObject(i));
                    }
                    data.add(row);
                }
            }
        } catch (SQLException e) {
            errorMsg = "SQL错误: " + e.getMessage();
        }
        return new QueryResult(columnNames, data, errorMsg);
    }

    /**
     * 执行更新 (INSERT, UPDATE, DELETE, TRANSACTION)
     */
    public static String executeUpdate(String sql) {
        try (Connection conn = getConnection();
             Statement stmt = conn.createStatement()) {

            // 执行 SQL (支持多条语句，例如事务块)
            stmt.executeUpdate(sql);
            return "执行成功";

        } catch (SQLException e) {
            e.printStackTrace();
            return "执行失败: " + e.getMessage();
        }
    }

    public static String executeBatch(String sqlScript) {
        try (Connection conn = getConnection();
             Statement stmt = conn.createStatement()) {
            String[] parts = sqlScript.split(";");
            int count = 0;
            for (String p : parts) {
                String s = p.trim();
                if (s.isEmpty()) continue;
                stmt.execute(s);
                count++;
            }
            return "执行成功，语句数: " + count;
        } catch (SQLException e) {
            e.printStackTrace();
            return "执行失败: " + e.getMessage();
        }
    }

    public static String executeBatchAdmin(String sqlScript) {
        String adminUser = "admin";
        String adminPass = "Admin@123";
        if (adminUser == null || adminPass == null) {
            return "执行失败: 未配置管理员凭据 OG_ADMIN_USER/OG_ADMIN_PASS";
        }
        try (Connection conn = DriverManager.getConnection(DB_URL, adminUser, adminPass);
             Statement stmt = conn.createStatement()) {
            String[] parts = sqlScript.split(";");
            int count = 0;
            for (String p : parts) {
                String s = p.trim();
                if (s.isEmpty()) continue;
                stmt.execute(s);
                count++;
            }
            return "执行成功，语句数: " + count;
        } catch (SQLException e) {
            e.printStackTrace();
            return "执行失败: " + e.getMessage();
        }
    }

    public static class QueryResult {
        public Vector<String> columnNames;
        public Vector<Vector<Object>> data;
        public String errorMsg;

        public QueryResult(Vector<String> c, Vector<Vector<Object>> d, String e) {
            this.columnNames = c;
            this.data = d;
            this.errorMsg = e;
        }
    }

    public static void main(String[] args) {
        String sql = "SELECT * FROM campus_card.users ORDER BY 1 LIMIT 10;";
        QueryResult qr = executeQuery(sql);
        if (qr.errorMsg != null) {
            System.out.println("查询失败: " + qr.errorMsg);
        } else {
            System.out.println("查询成功, 行数: " + qr.data.size() + ", 列数: " + qr.columnNames.size());
            for (int i = 0; i < qr.data.size(); i++) {
                System.out.println(qr.data.get(i));
            }
        }
    }
}
