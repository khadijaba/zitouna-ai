package tn.zitouna.ai.explain;

import static org.springframework.security.test.web.servlet.setup.SecurityMockMvcConfigurers.springSecurity;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.context.WebApplicationContext;

import com.jayway.jsonpath.JsonPath;
import com.sun.net.httpserver.HttpServer;

/** POST /api/ai/explain through the real security chain, with a local HTTP server standing in for M5. */
@SpringBootTest
@ActiveProfiles("test")
class ExplainControllerTest {

    private static final HttpServer M5 = startFakeM5();

    private static HttpServer startFakeM5() {
        try {
            HttpServer server = HttpServer.create(new InetSocketAddress("localhost", 0), 0);
            server.createContext("/explain", exchange -> {
                byte[] bytes = """
                        {"explanation":"Le modèle a reconnu l'œil de paon.","provider":"gemini",
                         "model":"gemini-3.5-flash","latencyMs":800,"fallback":false}"""
                        .getBytes(StandardCharsets.UTF_8);
                exchange.getResponseHeaders().add("Content-Type", "application/json");
                exchange.sendResponseHeaders(200, bytes.length);
                exchange.getResponseBody().write(bytes);
                exchange.close();
            });
            server.start();
            return server;
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    @DynamicPropertySource
    static void m5Url(DynamicPropertyRegistry registry) {
        registry.add("app.ai.assistant-url", () -> "http://localhost:" + M5.getAddress().getPort());
    }

    @Autowired
    private WebApplicationContext context;

    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        mvc = MockMvcBuilders.webAppContextSetup(context).apply(springSecurity()).build();
    }

    private String farmer(String email) throws Exception {
        String body = mvc.perform(post("/api/auth/register").contentType(MediaType.APPLICATION_JSON)
                .content("{\"fullName\":\"Farmer\",\"email\":\"" + email + "\",\"password\":\"zitouna123\"}"))
                .andExpect(status().isCreated()).andReturn().getResponse().getContentAsString();
        return "Bearer " + JsonPath.read(body, "$.token");
    }

    @Test
    void explainsTheResultAndRecordsItInTheHistory() throws Exception {
        String bearer = farmer("explain-ok@test.tn");
        mvc.perform(post("/api/ai/explain").header("Authorization", bearer).contentType(MediaType.APPLICATION_JSON)
                .content("{\"module\":\"M1\",\"result\":{\"labelFr\":\"Œil de paon\",\"confidence\":0.99}}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.explanation").value("Le modèle a reconnu l'œil de paon."))
                .andExpect(jsonPath("$.fallback").value(false));
        mvc.perform(get("/api/history").param("type", "EXPLAIN").header("Authorization", bearer))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.totalElements").value(1));
    }

    @Test
    void anonymousIsRefused() throws Exception {
        mvc.perform(post("/api/ai/explain").contentType(MediaType.APPLICATION_JSON)
                .content("{\"module\":\"M1\",\"result\":{}}"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void unknownModuleOrLanguageIsRejected() throws Exception {
        String bearer = farmer("explain-bad@test.tn");
        mvc.perform(post("/api/ai/explain").header("Authorization", bearer).contentType(MediaType.APPLICATION_JSON)
                .content("{\"module\":\"M9\",\"result\":{}}"))
                .andExpect(status().isBadRequest());
        mvc.perform(post("/api/ai/explain").header("Authorization", bearer).contentType(MediaType.APPLICATION_JSON)
                .content("{\"module\":\"M2\",\"result\":{},\"language\":\"en\"}"))
                .andExpect(status().isBadRequest());
    }
}
