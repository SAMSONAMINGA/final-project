plugins {
    id("com.android.application") apply false
    id("com.android.library") apply false
    kotlin("android") apply false
    id("com.google.dagger.hilt.android") apply false
    id("com.google.gms.google-services") apply false
}

buildscript {
    dependencies {
        classpath("com.google.dagger:hilt-android-gradle-plugin:2.48")
        classpath("com.google.gms:google-services:4.4.0")
    }
}

task<Delete>("clean") {
    delete(rootProject.buildDir)
}
