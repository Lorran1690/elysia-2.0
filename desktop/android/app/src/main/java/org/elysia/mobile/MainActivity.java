package org.elysia.mobile;

import android.graphics.Color;
import android.os.Bundle;
import android.view.View;
import androidx.core.graphics.Insets;
import androidx.core.view.ViewCompat;
import androidx.core.view.WindowCompat;
import androidx.core.view.WindowInsetsCompat;
import androidx.core.view.WindowInsetsControllerCompat;
import com.getcapacitor.BridgeActivity;

/** Bundled assets only. The app never starts the Windows/Python executable. */
public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(ElysiaUpdatesPlugin.class);
        super.onCreate(savedInstanceState);
        WindowCompat.setDecorFitsSystemWindows(getWindow(), false);
        View content = findViewById(android.R.id.content);
        content.setBackgroundColor(Color.rgb(14, 15, 21));
        WindowInsetsControllerCompat controller = new WindowInsetsControllerCompat(getWindow(), content);
        controller.setAppearanceLightStatusBars(false);
        controller.setAppearanceLightNavigationBars(false);
        // Keep the WebView itself outside system bars and camera cutouts on
        // portrait, landscape and Android 15/16 edge-to-edge windows. The CSS
        // follows the actual native IME visibility; an orientation resize alone
        // must not be mistaken for an open keyboard by the web interface.
        ViewCompat.setOnApplyWindowInsetsListener(content, (view, insets) -> {
            Insets bars = insets.getInsets(WindowInsetsCompat.Type.systemBars() | WindowInsetsCompat.Type.displayCutout());
            Insets ime = insets.getInsets(WindowInsetsCompat.Type.ime());
            view.setPadding(bars.left, bars.top, bars.right, Math.max(bars.bottom, ime.bottom));
            if (getBridge() != null) {
                boolean visible = insets.isVisible(WindowInsetsCompat.Type.ime());
                // Insets can arrive before Capacitor's bridge script or React
                // during a page reload. Standard DOM dispatch needs neither;
                // keep the latest real value for the initial React listener.
                getBridge().eval(
                    "window.__elysiaKeyboardVisible=" + visible + ";window.dispatchEvent(new CustomEvent('elysia-keyboard',{detail:{visible:" + visible + "}}));",
                    null
                );
            }
            return WindowInsetsCompat.CONSUMED;
        });
        ViewCompat.requestApplyInsets(content);
    }
}
