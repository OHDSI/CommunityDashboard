import { ComponentFixture, TestBed } from '@angular/core/testing';
import { RouterTestingModule } from '@angular/router/testing';

import { EhdenSummaryComponent } from './ehden-summary.component';

describe('EhdenSummaryComponent', () => {
  let component: EhdenSummaryComponent;
  let fixture: ComponentFixture<EhdenSummaryComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        EhdenSummaryComponent,
        RouterTestingModule,
      ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(EhdenSummaryComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
