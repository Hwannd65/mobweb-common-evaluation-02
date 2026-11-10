package com.example.photoviewer;

import static org.junit.Assert.*;
import android.content.Context;
import android.content.SharedPreferences;
import android.graphics.Bitmap;
import android.widget.FrameLayout;
import androidx.test.core.app.ApplicationProvider;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import java.util.Collections;
import java.util.UUID;
import org.junit.Test;
import org.junit.runner.RunWith;

@RunWith(AndroidJUnit4.class)
public class PhotoReviewTest {
    @Test public void reviewPersistsAndStaysAccountScoped() {
        Context context = ApplicationProvider.getApplicationContext();
        String name = "review_test_" + UUID.randomUUID();
        SharedPreferences first = context.getSharedPreferences(name, Context.MODE_PRIVATE);
        SharedPreferences other = context.getSharedPreferences(name + "_other", Context.MODE_PRIVATE);
        Bitmap image = Bitmap.createBitmap(2, 2, Bitmap.Config.ARGB_8888);
        PhotoPost post = new PhotoPost(7, 1, "author", "person", "person,", image,
                0, false, false, 0, false);
        androidx.test.platform.app.InstrumentationRegistry.getInstrumentation().runOnMainSync(() -> {
            ImageAdapter adapter = new ImageAdapter(p -> {}, p -> {});
            adapter.setReviewPreferences(first, () -> {});
            adapter.submitPosts(Collections.singletonList(post));
            assertEquals(1, adapter.unreadPhotoCount());
            ImageAdapter.ImageViewHolder holder = adapter.onCreateViewHolder(new FrameLayout(context), 0);
            adapter.onBindViewHolder(holder, 0);
            holder.reviewButton.performClick();
            assertEquals(0, adapter.unreadPhotoCount());
            ImageAdapter restored = new ImageAdapter(p -> {}, p -> {});
            restored.setReviewPreferences(context.getSharedPreferences(name, Context.MODE_PRIVATE), () -> {});
            restored.submitPosts(Collections.singletonList(post));
            assertEquals(0, restored.unreadPhotoCount());
            restored.setReviewPreferences(other, () -> {});
            assertEquals(1, restored.unreadPhotoCount());
        });
        first.edit().clear().commit();
        other.edit().clear().commit();
        image.recycle();
    }
}
