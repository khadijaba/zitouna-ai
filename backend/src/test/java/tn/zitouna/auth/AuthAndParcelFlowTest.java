package tn.zitouna.auth;

import static org.hamcrest.Matchers.hasSize;
import static org.springframework.security.test.web.servlet.setup.SecurityMockMvcConfigurers.springSecurity;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.context.WebApplicationContext;

import com.jayway.jsonpath.JsonPath;

/** End-to-end through the real security chain: register -> JWT -> protected endpoints. */
@SpringBootTest
@ActiveProfiles("test")
class AuthAndParcelFlowTest {

    @Autowired
    private WebApplicationContext context;

    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        mvc = MockMvcBuilders.webAppContextSetup(context).apply(springSecurity()).build();
    }

    @Test
    void protectedEndpointsRequireToken() throws Exception {
        mvc.perform(get("/api/parcels")).andExpect(status().isUnauthorized());
    }

    @Test
    void registerLoginAndManageParcels() throws Exception {
        String register = """
                {"fullName":"Salah Ben Ali","email":"salah@example.tn","password":"zitouna123"}""";
        mvc.perform(post("/api/auth/register").contentType(MediaType.APPLICATION_JSON).content(register))
                .andExpect(status().isCreated());

        // Same email twice -> 409
        mvc.perform(post("/api/auth/register").contentType(MediaType.APPLICATION_JSON).content(register))
                .andExpect(status().isConflict());

        // Wrong password -> 401
        mvc.perform(post("/api/auth/login").contentType(MediaType.APPLICATION_JSON)
                .content("""
                        {"email":"salah@example.tn","password":"wrong-password"}"""))
                .andExpect(status().isUnauthorized());

        String body = mvc.perform(post("/api/auth/login").contentType(MediaType.APPLICATION_JSON)
                .content("""
                        {"email":"salah@example.tn","password":"zitouna123"}"""))
                .andExpect(status().isOk())
                .andReturn().getResponse().getContentAsString();
        String bearer = "Bearer " + JsonPath.read(body, "$.token");

        mvc.perform(get("/api/users/me").header("Authorization", bearer))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.email").value("salah@example.tn"))
                .andExpect(jsonPath("$.role").value("FARMER"));

        String parcel = mvc.perform(post("/api/parcels").header("Authorization", bearer)
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                        {"name":"Henchir Sfax","governorate":"Sfax","latitude":34.74,"longitude":10.76,
                         "areaHa":2.5,"treeCount":250,"variety":"Chemlali","irrigated":false}"""))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.id").isNumber())
                .andReturn().getResponse().getContentAsString();
        Integer parcelId = JsonPath.read(parcel, "$.id");

        mvc.perform(get("/api/parcels").header("Authorization", bearer))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(1)));

        // AI services are not running in tests: the backend answers 503, it does not crash.
        mvc.perform(get("/api/ai/price").header("Authorization", bearer))
                .andExpect(status().isServiceUnavailable());

        // Harvest plan without image uses the saved tree count, then fails on M3 (down) -> 503.
        mvc.perform(post("/api/parcels/{id}/harvest-plan", parcelId).header("Authorization", bearer))
                .andExpect(status().isServiceUnavailable());

        // Another farmer cannot see this parcel.
        String other = mvc.perform(post("/api/auth/register").contentType(MediaType.APPLICATION_JSON)
                .content("""
                        {"fullName":"Other Farmer","email":"other@example.tn","password":"zitouna123"}"""))
                .andReturn().getResponse().getContentAsString();
        mvc.perform(get("/api/parcels/{id}", parcelId).header("Authorization", "Bearer " + JsonPath.read(other, "$.token")))
                .andExpect(status().isNotFound());
    }
}
