import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EhdenWelcomeComponent } from './ehden-welcome.component';

describe('PubMedWelcomeComponent', () => {
  let component: EhdenWelcomeComponent;
  let fixture: ComponentFixture<EhdenWelcomeComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ EhdenWelcomeComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(EhdenWelcomeComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
