import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';

import { PubMedTabsComponent } from './pub-med-tabs.component';

describe('PubMedTabsComponent', () => {
  let component: PubMedTabsComponent;
  let fixture: ComponentFixture<PubMedTabsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ 
        PubMedTabsComponent,
        NoopAnimationsModule,
      ],

    })
    .compileComponents();

    fixture = TestBed.createComponent(PubMedTabsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
