package tn.zitouna.status;

import static org.hamcrest.Matchers.containsString;
import static org.hamcrest.Matchers.hasSize;
import static org.springframework.security.test.web.servlet.setup.SecurityMockMvcConfigurers.springSecurity;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.context.WebApplicationContext;

/** The home page and /api/status are public; in tests the AI services are down (localhost:1). */
@SpringBootTest
@ActiveProfiles("test")
class StatusControllerTest {

    @Autowired
    private WebApplicationContext context;

    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        mvc = MockMvcBuilders.webAppContextSetup(context).apply(springSecurity()).build();
    }

    @Test
    void statusIsPublicAndReportsDatabaseAndSixModules() throws Exception {
        mvc.perform(get("/api/status"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.application.springBootVersion").isString())
                .andExpect(jsonPath("$.database.up").value(true))
                .andExpect(jsonPath("$.database.product").value("H2"))
                .andExpect(jsonPath("$.modules", hasSize(6)))
                .andExpect(jsonPath("$.modules[1].id").value("M2"))
                .andExpect(jsonPath("$.modules[3].id").value("M4"))
                .andExpect(jsonPath("$.modules[0].up").value(false))
                .andExpect(jsonPath("$.modules[0].modelLoaded").doesNotExist());
    }

    @Test
    void homePageIsServedWithoutToken() throws Exception {
        mvc.perform(get("/index.html"))
                .andExpect(status().isOk())
                .andExpect(content().string(containsString("Backend Zitouna AI")))
                .andExpect(content().string(containsString("api/status")));
    }

    @Test
    void protectedApiStillNeedsToken() throws Exception {
        mvc.perform(get("/api/history")).andExpect(status().isUnauthorized());
    }

    @Test
    void swaggerIsRemoved() throws Exception {
        mvc.perform(get("/swagger-ui.html")).andExpect(status().is4xxClientError());
        mvc.perform(get("/v3/api-docs")).andExpect(status().is4xxClientError());
    }
}
