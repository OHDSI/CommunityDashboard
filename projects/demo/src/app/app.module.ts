import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { NavigationComponent } from './navigation/navigation.component';
import { DocsMock } from './docs-mock.service';
import { SearchDocsService } from '@commonshcs-angular';

@NgModule({
  declarations: [
    AppComponent
  ],
  imports: [
    NavigationComponent,
    BrowserModule,
    AppRoutingModule,
    BrowserAnimationsModule
  ],
  providers: [
    {provide: 'DocsService', useClass: DocsMock},
    {provide: 'SearchService', useClass: SearchDocsService}
  ],
  bootstrap: [AppComponent]
})
export class AppModule { }
