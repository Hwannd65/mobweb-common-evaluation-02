package com.example.photoviewer;

import static androidx.test.espresso.Espresso.onView;
import static androidx.test.espresso.action.ViewActions.click;
import static androidx.test.espresso.matcher.ViewMatchers.withId;
import static org.junit.Assert.*;

import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.drawable.BitmapDrawable;
import androidx.recyclerview.widget.RecyclerView;
import androidx.test.core.app.ActivityScenario;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.platform.app.InstrumentationRegistry;
import androidx.test.uiautomator.By;
import androidx.test.uiautomator.UiDevice;
import androidx.test.uiautomator.Until;
import org.json.JSONArray;
import org.json.JSONObject;
import org.junit.Test;
import org.junit.runner.RunWith;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

/** Read-only verification: the latest real YOLO image must be displayed by the app. */
@RunWith(AndroidJUnit4.class)
public class IntruderImageSyncTest {
    @Test
    public void latestYoloImageIsDisplayed() throws Exception {
        HttpURLConnection api = (HttpURLConnection) new URL(
                MainActivity.SITE_URL + "/api_root/Post/?sort=newest").openConnection();
        api.setConnectTimeout(10000);
        api.setReadTimeout(10000);
        api.setRequestProperty("Accept", "application/json");
        JSONObject latest;
        try {
            assertEquals(200, api.getResponseCode());
            try (java.io.InputStream input = api.getInputStream()) {
                latest = new JSONArray(new String(input.readAllBytes(), StandardCharsets.UTF_8)).getJSONObject(0);
            }
        } finally {
            api.disconnect();
        }
        assertTrue("Create a YOLO detection before running this test",
                !latest.getString("title").isEmpty()
                        && latest.getString("text").contains(latest.getString("title")));
        Bitmap expected;
        try (java.io.InputStream input = new URL(latest.getString("image")).openStream()) {
            expected = BitmapFactory.decodeStream(input);
        }
        assertNotNull(expected);
        UiDevice device = UiDevice.getInstance(InstrumentationRegistry.getInstrumentation());
        try (ActivityScenario<MainActivity> scenario = ActivityScenario.launch(MainActivity.class)) {
            onView(withId(R.id.btn_load)).perform(click());
            assertTrue("The image list must finish loading",
                    device.wait(Until.hasObject(By.res(BuildConfig.APPLICATION_ID, "post_title")), 60000));
            onView(withId(R.id.recyclerView)).check((view, error) -> {
                if (error != null) throw error;
                RecyclerView list = (RecyclerView) view;
                ImageAdapter.ImageViewHolder first = (ImageAdapter.ImageViewHolder)
                        list.findViewHolderForAdapterPosition(0);
                assertNotNull(first);
                assertTrue(first.imageView.getDrawable() instanceof BitmapDrawable);
                Bitmap actual = ((BitmapDrawable) first.imageView.getDrawable()).getBitmap();
                assertTrue("The displayed bitmap must equal the newest YOLO image", expected.sameAs(actual));
            });
        }
    }
}
