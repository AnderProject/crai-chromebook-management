plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("com.google.devtools.ksp")
}

android {
    namespace = "com.crai.chromebook"
    compileSdk = 36
    buildToolsVersion = "36.1.0"

    defaultConfig {
        applicationId = "com.crai.chromebook"
        minSdk = 24          // Chromebooks corren Android 7+ en su contenedor
        targetSdk = 36
        versionCode = 1
        versionName = "1.0"

        // Defaults pre-cableados del kiosko: la app arranca ya configurada para
        // la demo, sin que nadie tenga que escribir nada en la Chromebook. El
        // personal aún puede sobreescribirlos desde ⚙ (protegido por PIN).
        buildConfigField("String", "DEFAULT_SERVER_URL", "\"http://192.168.100.7:8000/\"")
        buildConfigField("String", "DEFAULT_CODIGO", "\"CB-001\"")
        buildConfigField("String", "DEFAULT_API_KEY", "\"crai-kiosko-2026\"")
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
    buildFeatures {
        viewBinding = true
        buildConfig = true
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("com.google.android.material:material:1.12.0")
    implementation("androidx.constraintlayout:constraintlayout:2.1.4")
    implementation("androidx.activity:activity-ktx:1.9.1")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.4")

    // Room (caché local de reservas)
    implementation("androidx.room:room-runtime:2.6.1")
    implementation("androidx.room:room-ktx:2.6.1")
    ksp("androidx.room:room-compiler:2.6.1")

    // Coroutines
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")

    // Retrofit + Gson (Fase 4: sincronización con el backend Django)
    implementation("com.squareup.retrofit2:retrofit:2.11.0")
    implementation("com.squareup.retrofit2:converter-gson:2.11.0")

    // Coil: carga de la foto de perfil del estudiante en la sesión
    implementation("io.coil-kt:coil:2.6.0")

    // WorkManager (sync diferido cuando vuelva la red)
    implementation("androidx.work:work-runtime-ktx:2.9.0")
}
