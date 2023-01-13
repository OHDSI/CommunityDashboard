import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';

import { EhdenTabsComponent } from './ehden-tabs.component';

describe('EdgenTabsComponent', () => {
  let component: EhdenTabsComponent;
  let fixture: ComponentFixture<EhdenTabsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ 
        EhdenTabsComponent,
        NoopAnimationsModule,
      ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(EhdenTabsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
